"""
Unit tests for utility functions and services
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, time, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, Mock

from accounts.models import User
from patients.models import PatientProfile
from doctors.models import DoctorProfile, Specialization
from appointments.models import Appointment, AppointmentType
from notifications.models import EmailNotification, EmailTemplate
from notifications.services import EmailNotificationService, SMSNotificationService, NotificationAnalyticsService
from billing.services import InvoiceService, PaymentService

User = get_user_model()


class EmailNotificationServiceTest(TestCase):
    """Test cases for Email Notification Service"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        self.template = EmailTemplate.objects.create(
            name='Test Template',
            subject='Hello {{name}}',
            html_content='<p>Hello {{name}}, welcome!</p>',
            text_content='Hello {{name}}, welcome!'
        )
        self.service = EmailNotificationService()
    
    def test_send_notification_with_template(self):
        """Test sending notification with template"""
        notification = self.service.send_notification(
            template_type='test_template',
            recipient_email='test@example.com',
            recipient_user=self.user,
            variables={'name': 'John Doe'},
            priority='normal'
        )
        
        self.assertIsInstance(notification, EmailNotification)
        self.assertEqual(notification.recipient_email, 'test@example.com')
        self.assertEqual(notification.recipient_user, self.user)
        self.assertEqual(notification.priority, 'normal')
    
    def test_send_notification_without_template(self):
        """Test sending notification without template"""
        notification = self.service.send_notification(
            template_type=None,
            recipient_email='test@example.com',
            subject='Direct Email',
            html_content='<p>Direct content</p>',
            text_content='Direct content',
            priority='high'
        )
        
        self.assertIsInstance(notification, EmailNotification)
        self.assertEqual(notification.subject, 'Direct Email')
        self.assertEqual(notification.priority, 'high')
    
    @patch('notifications.services.send_mail')
    def test_process_email_queue(self, mock_send_mail):
        """Test processing email queue"""
        mock_send_mail.return_value = True
        
        # Create pending notification
        notification = EmailNotification.objects.create(
            recipient_email='test@example.com',
            subject='Test Email',
            html_content='<p>Test content</p>',
            text_content='Test content',
            status='pending'
        )
        
        # Process queue
        processed = self.service.process_email_queue()
        
        # Verify
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'sent')
        self.assertEqual(processed, 1)
        mock_send_mail.assert_called_once()
    
    def test_get_email_analytics(self):
        """Test getting email analytics"""
        # Create test notifications
        EmailNotification.objects.create(
            recipient_email='test1@example.com',
            subject='Test 1',
            status='sent'
        )
        EmailNotification.objects.create(
            recipient_email='test2@example.com',
            subject='Test 2',
            status='delivered'
        )
        EmailNotification.objects.create(
            recipient_email='test3@example.com',
            subject='Test 3',
            status='failed'
        )
        
        analytics = self.service.get_email_analytics()
        
        self.assertEqual(analytics['total_emails'], 3)
        self.assertEqual(analytics['sent_emails'], 1)
        self.assertEqual(analytics['delivered_emails'], 1)
        self.assertEqual(analytics['failed_emails'], 1)
        self.assertEqual(analytics['delivery_rate'], 33.33)


class SMSNotificationServiceTest(TestCase):
    """Test cases for SMS Notification Service"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        self.service = SMSNotificationService()
    
    @patch('notifications.services.TwilioSMSProvider.send_sms')
    def test_send_sms_notification(self, mock_send_sms):
        """Test sending SMS notification"""
        mock_send_sms.return_value = {
            'success': True,
            'message_id': 'SMS123456',
            'cost': 0.05
        }
        
        notification = self.service.send_notification(
            template_type='test_sms',
            recipient_phone='+1234567890',
            recipient_user=self.user,
            variables={'name': 'John Doe'},
            priority='normal'
        )
        
        self.assertEqual(notification.recipient_phone, '+1234567890')
        self.assertEqual(notification.status, 'sent')
        mock_send_sms.assert_called_once()
    
    def test_get_sms_analytics(self):
        """Test getting SMS analytics"""
        from notifications.models import SMSNotification
        
        # Create test SMS notifications
        SMSNotification.objects.create(
            recipient_phone='+1234567890',
            message='Test message 1',
            status='sent',
            cost=Decimal('0.05')
        )
        SMSNotification.objects.create(
            recipient_phone='+1234567891',
            message='Test message 2',
            status='delivered',
            cost=Decimal('0.05')
        )
        
        analytics = self.service.get_sms_analytics()
        
        self.assertEqual(analytics['total_sms'], 2)
        self.assertEqual(analytics['total_cost'], 0.10)
        self.assertEqual(analytics['average_cost'], 0.05)


class NotificationAnalyticsServiceTest(TestCase):
    """Test cases for Notification Analytics Service"""
    
    def setUp(self):
        self.service = NotificationAnalyticsService()
        self.user = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
    
    def test_generate_analytics_report(self):
        """Test generating analytics report"""
        # Create test data
        EmailNotification.objects.create(
            recipient_email='test@example.com',
            subject='Test Email',
            status='delivered'
        )
        
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        
        report = self.service.generate_analytics_report(
            start_date=start_date,
            end_date=end_date,
            report_type='weekly'
        )
        
        self.assertEqual(report.report_type, 'weekly')
        self.assertEqual(report.start_date, start_date)
        self.assertEqual(report.end_date, end_date)
        self.assertEqual(report.total_notifications, 1)
    
    def test_track_notification_event(self):
        """Test tracking notification events"""
        event = self.service.track_notification_event(
            event_type='opened',
            notification_type='appointment_reminder',
            notification_channel='email',
            notification_id='12345678-1234-1234-1234-123456789012',
            recipient_user=self.user,
            recipient_email='test@example.com'
        )
        
        self.assertEqual(event.event_type, 'opened')
        self.assertEqual(event.notification_channel, 'email')
        self.assertEqual(event.recipient_user, self.user)
    
    def test_get_user_engagement_metrics(self):
        """Test getting user engagement metrics"""
        # Create test events
        self.service.track_notification_event(
            event_type='sent',
            notification_type='test',
            notification_channel='email',
            notification_id='12345678-1234-1234-1234-123456789012',
            recipient_user=self.user
        )
        self.service.track_notification_event(
            event_type='opened',
            notification_type='test',
            notification_channel='email',
            notification_id='12345678-1234-1234-1234-123456789012',
            recipient_user=self.user
        )
        
        metrics = self.service.get_user_engagement_metrics(self.user, days=30)
        
        self.assertEqual(metrics['user_id'], self.user.id)
        self.assertEqual(metrics['total_sent'], 1)
        self.assertEqual(metrics['total_opened'], 1)
        self.assertEqual(metrics['open_rate'], 100.0)


class InvoiceServiceTest(TestCase):
    """Test cases for Invoice Service"""
    
    def setUp(self):
        self.patient_user = User.objects.create_user(
            username='patient1',
            email='patient1@example.com',
            password='pass123',
            user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        self.service = InvoiceService()
    
    def test_create_invoice_from_appointment(self):
        """Test creating invoice from appointment"""
        # Create appointment
        doctor_user = User.objects.create_user(
            username='doctor1', email='doctor1@example.com', password='pass123', user_type='doctor'
        )
        specialization = Specialization.objects.create(name='General Medicine')
        doctor = DoctorProfile.objects.create(
            user=doctor_user, license_number='MD123456', specialization=specialization
        )
        appointment_type = AppointmentType.objects.create(
            name='Consultation', duration=30, price=Decimal('100.00')
        )
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=doctor,
            appointment_date=date.today(),
            appointment_time=time(14, 30),
            appointment_type=appointment_type,
            status='completed'
        )
        
        invoice = self.service.create_invoice_from_appointment(appointment)
        
        self.assertEqual(invoice.patient, self.patient)
        self.assertEqual(invoice.amount, Decimal('100.00'))
        self.assertIn('Consultation', invoice.description)
    
    def test_calculate_invoice_total(self):
        """Test calculating invoice total"""
        services = [
            {'name': 'Consultation', 'price': Decimal('100.00')},
            {'name': 'Lab Test', 'price': Decimal('50.00')},
            {'name': 'X-Ray', 'price': Decimal('75.00')}
        ]
        
        total = self.service.calculate_invoice_total(services)
        self.assertEqual(total, Decimal('225.00'))
    
    def test_apply_discount(self):
        """Test applying discount to invoice"""
        from billing.models import Invoice
        
        invoice = Invoice.objects.create(
            patient=self.patient,
            amount=Decimal('100.00'),
            due_date=date.today() + timedelta(days=30)
        )
        
        discounted_invoice = self.service.apply_discount(invoice, Decimal('10.00'))
        
        self.assertEqual(discounted_invoice.amount, Decimal('90.00'))
        self.assertEqual(discounted_invoice.discount_amount, Decimal('10.00'))


class PaymentServiceTest(TestCase):
    """Test cases for Payment Service"""
    
    def setUp(self):
        self.patient_user = User.objects.create_user(
            username='patient1',
            email='patient1@example.com',
            password='pass123',
            user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        self.service = PaymentService()
    
    def test_process_payment(self):
        """Test processing payment"""
        from billing.models import Invoice, Payment
        
        invoice = Invoice.objects.create(
            patient=self.patient,
            amount=Decimal('100.00'),
            due_date=date.today() + timedelta(days=30)
        )
        
        payment = self.service.process_payment(
            invoice=invoice,
            amount=Decimal('100.00'),
            payment_method='credit_card',
            transaction_id='TXN123456'
        )
        
        self.assertEqual(payment.amount, Decimal('100.00'))
        self.assertEqual(payment.payment_method, 'credit_card')
        self.assertEqual(payment.status, 'completed')
        
        # Check invoice status
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'paid')
    
    def test_process_partial_payment(self):
        """Test processing partial payment"""
        from billing.models import Invoice
        
        invoice = Invoice.objects.create(
            patient=self.patient,
            amount=Decimal('100.00'),
            due_date=date.today() + timedelta(days=30)
        )
        
        payment = self.service.process_payment(
            invoice=invoice,
            amount=Decimal('50.00'),
            payment_method='credit_card',
            transaction_id='TXN123456'
        )
        
        self.assertEqual(payment.amount, Decimal('50.00'))
        
        # Check invoice status (should still be pending)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'partially_paid')
        self.assertEqual(invoice.paid_amount, Decimal('50.00'))
    
    def test_refund_payment(self):
        """Test refunding payment"""
        from billing.models import Invoice, Payment
        
        invoice = Invoice.objects.create(
            patient=self.patient,
            amount=Decimal('100.00'),
            due_date=date.today() + timedelta(days=30),
            status='paid'
        )
        
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal('100.00'),
            payment_method='credit_card',
            transaction_id='TXN123456',
            status='completed'
        )
        
        refund = self.service.refund_payment(payment, Decimal('100.00'), 'Customer request')
        
        self.assertEqual(refund.amount, Decimal('-100.00'))
        self.assertEqual(refund.payment_method, 'refund')
        self.assertIn('Customer request', refund.notes)
        
        # Check original payment status
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'refunded')
