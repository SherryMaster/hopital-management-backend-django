from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import datetime, timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import (
    EmailTemplate, EmailNotification, EmailConfiguration,
    EmailSubscription, EmailAnalytics,
    SMSTemplate, SMSNotification, SMSConfiguration, SMSAnalytics,
    PushNotificationTemplate, PushNotification, PushNotificationConfiguration,
    PushNotificationAnalytics, DeviceToken,
    TemplateVariable, TemplateLanguage, UnifiedTemplate, TemplateContent, TemplateUsageLog,
    NotificationPreference, NotificationSettings, NotificationBlacklist, NotificationSchedule
)
from .serializers import (
    EmailTemplateSerializer, EmailTemplateListSerializer,
    EmailNotificationSerializer, EmailNotificationListSerializer,
    EmailConfigurationSerializer, EmailSubscriptionSerializer,
    EmailAnalyticsSerializer, SendEmailSerializer, BulkEmailSerializer,
    EmailStatsSerializer, EmailTemplatePreviewSerializer,
    EmailDeliveryStatusSerializer,
    SMSTemplateSerializer, SMSNotificationSerializer, SendSMSSerializer,
    PushNotificationTemplateSerializer, PushNotificationSerializer,
    SendPushNotificationSerializer, RegisterDeviceTokenSerializer,
    TemplateVariableSerializer, TemplateLanguageSerializer, UnifiedTemplateSerializer,
    CreateUnifiedTemplateSerializer, RenderTemplateSerializer,
    NotificationPreferenceSerializer, NotificationSettingsSerializer,
    UpdatePreferencesSerializer, PreferenceCheckSerializer
)
from .services import (
    EmailNotificationService, EmailTemplateService, SMSNotificationService, SMSTemplateService,
    PushNotificationService, PushNotificationTemplateService,
    UnifiedTemplateService, TemplateVariableService, NotificationPreferenceService
)
from accounts.models import UserActivity


@extend_schema(tags=['Notification Templates'])
class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing email templates
    """
    queryset = EmailTemplate.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return EmailTemplateListSerializer
        return EmailTemplateSerializer

    def get_queryset(self):
        """
        Filter templates based on user permissions
        """
        user = self.request.user

        if hasattr(user, 'user_type') and user.user_type in ['admin', 'staff']:
            return EmailTemplate.objects.all()
        else:
            # Regular users can only view active templates
            return EmailTemplate.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

        # Log activity
        UserActivity.objects.create(
            user=self.request.user,
            action='create',
            resource_type='email_template',
            resource_id=str(serializer.instance.id),
            description=f'Created email template: {serializer.instance.name}',
            ip_address=self.request.META.get('REMOTE_ADDR', ''),
        )

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        Preview email template with sample variables
        """
        template = self.get_object()
        serializer = EmailTemplatePreviewSerializer(data=request.data)

        if serializer.is_valid():
            variables = serializer.validated_data['variables']

            try:
                template_service = EmailTemplateService()
                rendered_content = template_service.render_template(template, variables)

                return Response({
                    'subject': rendered_content['subject'],
                    'html_content': rendered_content['html_content'],
                    'text_content': rendered_content['text_content'],
                    'variables_used': variables
                })
            except Exception as e:
                return Response(
                    {'error': f'Template rendering failed: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Get available template types
        """
        template_types = [
            {'value': choice[0], 'label': choice[1]}
            for choice in EmailTemplate.TEMPLATE_TYPES
        ]
        return Response(template_types)


@extend_schema(tags=['Email Notifications'])
class EmailNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing email notifications
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return EmailNotificationListSerializer
        return EmailNotificationSerializer

    def get_queryset(self):
        """
        Filter notifications based on user permissions
        """
        user = self.request.user

        if hasattr(user, 'user_type') and user.user_type in ['admin', 'staff']:
            return EmailNotification.objects.select_related(
                'template', 'recipient_user', 'created_by'
            ).all()
        else:
            # Users can only see their own notifications
            return EmailNotification.objects.select_related(
                'template', 'recipient_user', 'created_by'
            ).filter(recipient_user=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def send_email(self, request):
        """
        Send a single email notification
        """
        serializer = SendEmailSerializer(data=request.data)

        if serializer.is_valid():
            try:
                email_service = EmailNotificationService()
                notification = email_service.send_notification(
                    template_type=serializer.validated_data['template_type'],
                    recipient_email=serializer.validated_data['recipient_email'],
                    variables=serializer.validated_data['variables'],
                    priority=serializer.validated_data.get('priority', 'normal'),
                    scheduled_at=serializer.validated_data.get('scheduled_at')
                )

                # Log activity
                UserActivity.objects.create(
                    user=request.user,
                    action='send',
                    resource_type='email_notification',
                    resource_id=str(notification.id),
                    description=f'Sent email to {notification.recipient_email}',
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )

                return Response(
                    EmailNotificationSerializer(notification).data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get email notification statistics
        """
        # Date range parameters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if not date_from:
            date_from = timezone.now().date() - timedelta(days=30)
        else:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()

        if not date_to:
            date_to = timezone.now().date()
        else:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        # Base queryset
        queryset = self.get_queryset().filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to
        )

        # Calculate statistics
        total_sent = queryset.count()
        total_delivered = queryset.filter(status='delivered').count()
        total_opened = queryset.filter(status='opened').count()
        total_clicked = queryset.filter(status='clicked').count()
        total_bounced = queryset.filter(status='bounced').count()
        total_failed = queryset.filter(status='failed').count()

        # Calculate rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
        click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0
        bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0

        # Template breakdown
        template_stats = {}
        template_breakdown = queryset.values(
            'template__template_type', 'template__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        for item in template_breakdown:
            template_type = item['template__template_type']
            if template_type not in template_stats:
                template_stats[template_type] = {
                    'total': 0,
                    'templates': []
                }
            template_stats[template_type]['total'] += item['count']
            template_stats[template_type]['templates'].append({
                'name': item['template__name'],
                'count': item['count']
            })

        # Recent notifications
        recent_notifications = queryset.order_by('-created_at')[:10]

        stats_data = {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'total_bounced': total_bounced,
            'total_failed': total_failed,
            'delivery_rate': round(delivery_rate, 2),
            'open_rate': round(open_rate, 2),
            'click_rate': round(click_rate, 2),
            'bounce_rate': round(bounce_rate, 2),
            'template_stats': template_stats,
            'recent_notifications': EmailNotificationListSerializer(recent_notifications, many=True).data,
            'date_from': date_from,
            'date_to': date_to
        }

        return Response(stats_data)


@extend_schema(tags=['Notification Templates'])
class SMSTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing SMS templates
    """
    queryset = SMSTemplate.objects.all()
    serializer_class = SMSTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter templates based on user permissions
        """
        user = self.request.user

        if hasattr(user, 'user_type') and user.user_type in ['admin', 'staff']:
            return SMSTemplate.objects.all()
        else:
            # Regular users can only view active templates
            return SMSTemplate.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

        # Log activity
        UserActivity.objects.create(
            user=self.request.user,
            action='create',
            resource_type='sms_template',
            resource_id=str(serializer.instance.id),
            description=f'Created SMS template: {serializer.instance.name}',
            ip_address=self.request.META.get('REMOTE_ADDR', ''),
        )

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        Preview SMS template with sample variables
        """
        template = self.get_object()
        variables = request.data.get('variables', {})

        try:
            template_service = SMSTemplateService()
            rendered_message = template_service.render_template(template, variables)

            return Response({
                'message': rendered_message,
                'message_length': len(rendered_message),
                'max_length': template.max_length,
                'variables_used': variables
            })
        except Exception as e:
            return Response(
                {'error': f'Template rendering failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Get available SMS template types
        """
        template_types = [
            {'value': choice[0], 'label': choice[1]}
            for choice in SMSTemplate.TEMPLATE_TYPES
        ]
        return Response(template_types)


@extend_schema(tags=['SMS Notifications'])
class SMSNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing SMS notifications
    """
    serializer_class = SMSNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter notifications based on user permissions
        """
        user = self.request.user

        if hasattr(user, 'user_type') and user.user_type in ['admin', 'staff']:
            return SMSNotification.objects.select_related(
                'template', 'recipient_user', 'created_by'
            ).all()
        else:
            # Users can only see their own notifications
            return SMSNotification.objects.select_related(
                'template', 'recipient_user', 'created_by'
            ).filter(recipient_user=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def send_sms(self, request):
        """
        Send a single SMS notification
        """
        serializer = SendSMSSerializer(data=request.data)

        if serializer.is_valid():
            try:
                sms_service = SMSNotificationService()
                notification = sms_service.send_notification(
                    template_type=serializer.validated_data['template_type'],
                    recipient_phone=serializer.validated_data['recipient_phone'],
                    variables=serializer.validated_data['variables'],
                    priority=serializer.validated_data.get('priority', 'normal'),
                    scheduled_at=serializer.validated_data.get('scheduled_at')
                )

                # Log activity
                UserActivity.objects.create(
                    user=request.user,
                    action='send',
                    resource_type='sms_notification',
                    resource_id=str(notification.id),
                    description=f'Sent SMS to {notification.recipient_phone}',
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )

                return Response(
                    SMSNotificationSerializer(notification).data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get SMS notification statistics
        """
        # Date range parameters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if not date_from:
            date_from = timezone.now().date() - timedelta(days=30)
        else:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()

        if not date_to:
            date_to = timezone.now().date()
        else:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        # Base queryset
        queryset = self.get_queryset().filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to
        )

        # Calculate statistics
        total_sent = queryset.count()
        total_delivered = queryset.filter(status='delivered').count()
        total_failed = queryset.filter(status='failed').count()
        total_undelivered = queryset.filter(status='undelivered').count()

        # Calculate rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        failure_rate = (total_failed / total_sent * 100) if total_sent > 0 else 0

        # Cost analysis
        total_cost = sum(
            notification.cost for notification in queryset
            if notification.cost is not None
        )
        average_cost = (total_cost / total_sent) if total_sent > 0 else 0

        stats_data = {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_failed': total_failed,
            'total_undelivered': total_undelivered,
            'delivery_rate': round(delivery_rate, 2),
            'failure_rate': round(failure_rate, 2),
            'total_cost': float(total_cost),
            'average_cost_per_sms': float(average_cost),
            'date_from': date_from,
            'date_to': date_to
        }

        return Response(stats_data)


@extend_schema(tags=['Notification Templates'])
class PushNotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing push notification templates
    """
    queryset = PushNotificationTemplate.objects.all()
    serializer_class = PushNotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter templates based on user permissions
        """
        user = self.request.user

        if hasattr(user, 'user_type') and user.user_type in ['admin', 'staff']:
            return PushNotificationTemplate.objects.all()
        else:
            # Regular users can only view active templates
            return PushNotificationTemplate.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

        # Log activity
        UserActivity.objects.create(
            user=self.request.user,
            action='create',
            resource_type='push_notification_template',
            resource_id=str(serializer.instance.id),
            description=f'Created push notification template: {serializer.instance.name}',
            ip_address=self.request.META.get('REMOTE_ADDR', ''),
        )

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        Preview push notification template with sample variables
        """
        template = self.get_object()
        variables = request.data.get('variables', {})

        try:
            template_service = PushNotificationTemplateService()
            rendered_content = template_service.render_template(template, variables)

            return Response({
                'title': rendered_content['title'],
                'body': rendered_content['body'],
                'icon_url': rendered_content.get('icon_url', ''),
                'image_url': rendered_content.get('image_url', ''),
                'action_url': rendered_content.get('action_url', ''),
                'variables_used': variables
            })
        except Exception as e:
            return Response(
                {'error': f'Template rendering failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Get available push notification template types
        """
        template_types = [
            {'value': choice[0], 'label': choice[1]}
            for choice in PushNotificationTemplate.TEMPLATE_TYPES
        ]
        return Response(template_types)


@extend_schema(tags=['Push Notifications'])
class PushNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing push notifications
    """
    serializer_class = PushNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter notifications based on user permissions
        """
        user = self.request.user

        if hasattr(user, 'user_type') and user.user_type in ['admin', 'staff']:
            return PushNotification.objects.select_related(
                'template', 'recipient_user', 'created_by'
            ).all()
        else:
            # Users can only see their own notifications
            return PushNotification.objects.select_related(
                'template', 'recipient_user', 'created_by'
            ).filter(recipient_user=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def send_push(self, request):
        """
        Send a push notification
        """
        serializer = SendPushNotificationSerializer(data=request.data)

        if serializer.is_valid():
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()

                recipient_user = User.objects.get(id=serializer.validated_data['recipient_user_id'])

                push_service = PushNotificationService()
                notification = push_service.send_notification(
                    template_type=serializer.validated_data['template_type'],
                    recipient_user=recipient_user,
                    variables=serializer.validated_data['variables'],
                    device_type=serializer.validated_data.get('device_type', 'web'),
                    priority=serializer.validated_data.get('priority', 'normal'),
                    scheduled_at=serializer.validated_data.get('scheduled_at'),
                    custom_data=serializer.validated_data.get('custom_data')
                )

                # Log activity
                UserActivity.objects.create(
                    user=request.user,
                    action='send',
                    resource_type='push_notification',
                    resource_id=str(notification.id),
                    description=f'Sent push notification to {recipient_user.get_full_name()}',
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )

                return Response(
                    PushNotificationSerializer(notification).data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def register_device(self, request):
        """
        Register device token for push notifications
        """
        serializer = RegisterDeviceTokenSerializer(data=request.data)

        if serializer.is_valid():
            try:
                push_service = PushNotificationService()
                device = push_service.register_device_token(
                    user=request.user,
                    device_token=serializer.validated_data['device_token'],
                    device_type=serializer.validated_data['device_type'],
                    device_name=serializer.validated_data.get('device_name', ''),
                    user_agent=serializer.validated_data.get('user_agent', ''),
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )

                return Response({
                    'message': 'Device token registered successfully',
                    'device_id': str(device.id),
                    'device_type': device.device_type
                })
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Notification Templates'])
class UnifiedTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing unified templates
    """
    queryset = UnifiedTemplate.objects.all()
    serializer_class = UnifiedTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter templates based on user permissions
        """
        user = self.request.user

        if hasattr(user, 'user_type') and user.user_type in ['admin', 'staff']:
            return UnifiedTemplate.objects.all()
        else:
            # Regular users can only view active templates
            return UnifiedTemplate.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

        # Log activity
        UserActivity.objects.create(
            user=self.request.user,
            action='create',
            resource_type='unified_template',
            resource_id=str(serializer.instance.id),
            description=f'Created unified template: {serializer.instance.name}',
            ip_address=self.request.META.get('REMOTE_ADDR', ''),
        )

    @action(detail=False, methods=['post'])
    def create_template(self, request):
        """
        Create a unified template with content
        """
        serializer = CreateUnifiedTemplateSerializer(data=request.data)

        if serializer.is_valid():
            try:
                template_service = UnifiedTemplateService()
                template = template_service.create_template(
                    name=serializer.validated_data['name'],
                    template_type=serializer.validated_data['template_type'],
                    supported_channels=serializer.validated_data['supported_channels'],
                    content_data=serializer.validated_data['content_data'],
                    variables=serializer.validated_data.get('variables', []),
                    created_by=request.user
                )

                return Response(
                    UnifiedTemplateSerializer(template).data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def render_template(self, request):
        """
        Render a template for specific channel and language
        """
        serializer = RenderTemplateSerializer(data=request.data)

        if serializer.is_valid():
            try:
                template = UnifiedTemplate.objects.get(id=serializer.validated_data['template_id'])

                template_service = UnifiedTemplateService()
                rendered_content = template_service.render_template(
                    template=template,
                    channel=serializer.validated_data['channel'],
                    language_code=serializer.validated_data['language_code'],
                    variables=serializer.validated_data['variables']
                )

                return Response({
                    'template_name': template.name,
                    'channel': serializer.validated_data['channel'],
                    'language_code': serializer.validated_data['language_code'],
                    'rendered_content': rendered_content,
                    'variables_used': serializer.validated_data['variables']
                })
            except UnifiedTemplate.DoesNotExist:
                return Response(
                    {'error': 'Template not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Notification Preferences'])
class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notification preferences
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return preferences for the current user
        """
        return NotificationPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """
        Bulk update notification preferences
        """
        serializer = UpdatePreferencesSerializer(data=request.data)

        if serializer.is_valid():
            try:
                updated_count = 0
                for pref_data in serializer.validated_data['preferences']:
                    preference, created = NotificationPreference.objects.update_or_create(
                        user=request.user,
                        notification_type=pref_data['notification_type'],
                        channel=pref_data['channel'],
                        defaults={
                            'is_enabled': pref_data['is_enabled'],
                            'frequency': pref_data.get('frequency', 'immediate'),
                            'priority_threshold': pref_data.get('priority_threshold', 'low')
                        }
                    )
                    updated_count += 1

                return Response({
                    'message': f'Updated {updated_count} preferences successfully',
                    'updated_count': updated_count
                })
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def check_preference(self, request):
        """
        Check if user wants to receive a specific notification
        """
        serializer = PreferenceCheckSerializer(data=request.data)

        if serializer.is_valid():
            try:
                preference_service = NotificationPreferenceService()

                # Check user preference
                should_receive = preference_service.check_user_preference(
                    user=request.user,
                    notification_type=serializer.validated_data['notification_type'],
                    channel=serializer.validated_data['channel'],
                    priority=serializer.validated_data.get('priority', 'normal')
                )

                # Check blacklist if contact info provided
                is_blacklisted = False
                contact_info = serializer.validated_data.get('contact_info')
                if contact_info:
                    blacklist_type = 'email' if '@' in contact_info else 'phone'
                    is_blacklisted = preference_service.is_blacklisted(
                        user=request.user,
                        contact_info=contact_info,
                        blacklist_type=blacklist_type
                    )

                # Check schedule
                should_send_now = preference_service.should_send_during_schedule(
                    user=request.user,
                    notification_type=serializer.validated_data['notification_type']
                )

                # Get user language
                user_language = preference_service.get_user_language(
                    user=request.user,
                    notification_type=serializer.validated_data['notification_type']
                )

                return Response({
                    'should_receive': should_receive,
                    'is_blacklisted': is_blacklisted,
                    'should_send_now': should_send_now,
                    'user_language': user_language,
                    'final_decision': should_receive and not is_blacklisted and should_send_now
                })
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def create_defaults(self, request):
        """
        Create default preferences for the user
        """
        try:
            preference_service = NotificationPreferenceService()
            preferences = preference_service.create_default_preferences(request.user)

            return Response({
                'message': f'Created {len(preferences)} default preferences',
                'preferences_count': len(preferences)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(tags=['Notification Preferences'])
class NotificationSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notification settings
    """
    serializer_class = NotificationSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return settings for the current user
        """
        return NotificationSettings.objects.filter(user=self.request.user)

    def get_object(self):
        """
        Get or create notification settings for the current user
        """
        settings, created = NotificationSettings.objects.get_or_create(
            user=self.request.user,
            defaults={}
        )
        return settings

    @action(detail=False, methods=['get'])
    def my_settings(self, request):
        """
        Get current user's notification settings
        """
        settings = self.get_object()
        return Response(NotificationSettingsSerializer(settings).data)

    @action(detail=False, methods=['post'])
    def update_settings(self, request):
        """
        Update current user's notification settings
        """
        settings = self.get_object()
        serializer = NotificationSettingsSerializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
