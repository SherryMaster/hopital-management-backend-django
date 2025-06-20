import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from billing.models import (
    Service, ServiceCategory, PricingTier, ServicePricing, DynamicPricingRule,
    ServiceBundle, BundleService, InvoiceItem
)
from accounts.models import User

def test_pricing_management_system():
    print("=== Testing Pricing and Service Management System ===")
    
    # Get required objects
    user = User.objects.filter(user_type='admin').first()
    
    print(f'User: {user.get_full_name() if user else "No admin user"}')
    
    # Test 1: Create pricing tiers
    print('\n1. Creating pricing tiers...')
    
    # Standard pricing tier
    standard_tier = PricingTier.objects.create(
        name='Standard Pricing',
        tier_type='standard',
        description='Standard pricing for regular patients',
        discount_percentage=Decimal('0.00'),
        markup_percentage=Decimal('0.00'),
        is_active=True,
        priority=1
    )
    
    # Senior citizen discount tier
    senior_tier = PricingTier.objects.create(
        name='Senior Citizen Discount',
        tier_type='senior',
        description='Discounted pricing for senior citizens (65+)',
        discount_percentage=Decimal('15.00'),
        markup_percentage=Decimal('0.00'),
        minimum_age=65,
        requires_verification=True,
        is_active=True,
        priority=2
    )
    
    # Insurance tier
    insurance_tier = PricingTier.objects.create(
        name='Insurance Pricing',
        tier_type='insurance',
        description='Negotiated rates for insurance companies',
        discount_percentage=Decimal('20.00'),
        markup_percentage=Decimal('0.00'),
        requires_verification=True,
        is_active=True,
        priority=3
    )
    
    print(f'✓ Created standard tier: {standard_tier.name}')
    print(f'✓ Created senior tier: {senior_tier.name} ({senior_tier.discount_percentage}% discount)')
    print(f'✓ Created insurance tier: {insurance_tier.name} ({insurance_tier.discount_percentage}% discount)')
    
    # Test 2: Create service pricing
    print('\n2. Creating service pricing...')
    
    # Get existing services
    services = Service.objects.filter(is_active=True)[:3]
    
    if services.exists():
        for service in services:
            # Standard pricing
            standard_pricing = ServicePricing.objects.create(
                service=service,
                pricing_tier=standard_tier,
                price=service.base_price,
                minimum_price=service.base_price * Decimal('0.8'),
                maximum_price=service.base_price * Decimal('1.2'),
                effective_from=timezone.now().date(),
                is_active=True
            )
            
            # Senior pricing (15% discount)
            senior_price = service.base_price * (1 - senior_tier.discount_percentage / 100)
            senior_pricing = ServicePricing.objects.create(
                service=service,
                pricing_tier=senior_tier,
                price=senior_price,
                minimum_price=senior_price * Decimal('0.9'),
                maximum_price=senior_price * Decimal('1.1'),
                effective_from=timezone.now().date(),
                is_active=True
            )
            
            # Insurance pricing (20% discount)
            insurance_price = service.base_price * (1 - insurance_tier.discount_percentage / 100)
            insurance_pricing = ServicePricing.objects.create(
                service=service,
                pricing_tier=insurance_tier,
                price=insurance_price,
                minimum_price=insurance_price * Decimal('0.9'),
                maximum_price=insurance_price * Decimal('1.1'),
                effective_from=timezone.now().date(),
                is_active=True
            )
            
            print(f'✓ Created pricing for {service.name}:')
            print(f'  Standard: ${standard_pricing.price}')
            print(f'  Senior: ${senior_pricing.price}')
            print(f'  Insurance: ${insurance_pricing.price}')
    
    # Test 3: Create dynamic pricing rules
    print('\n3. Creating dynamic pricing rules...')
    
    # Emergency pricing rule (25% markup)
    emergency_rule = DynamicPricingRule.objects.create(
        name='Emergency Service Markup',
        rule_type='emergency',
        description='25% markup for emergency services outside business hours',
        conditions={
            'time_conditions': {
                'after_hours': True,
                'weekends': True,
                'holidays': True
            },
            'service_types': ['emergency', 'urgent_care']
        },
        adjustment_type='percentage',
        adjustment_value=Decimal('25.00'),
        minimum_adjustment=Decimal('10.00'),
        maximum_adjustment=Decimal('100.00'),
        effective_from=timezone.now(),
        is_active=True,
        priority=1
    )
    
    # Volume discount rule
    volume_rule = DynamicPricingRule.objects.create(
        name='Volume Discount',
        rule_type='volume_based',
        description='5% discount for patients with 5+ visits this month',
        conditions={
            'minimum_visits': 5,
            'period': 'monthly'
        },
        adjustment_type='percentage',
        adjustment_value=Decimal('-5.00'),  # Negative for discount
        minimum_adjustment=Decimal('-20.00'),
        maximum_adjustment=Decimal('0.00'),
        effective_from=timezone.now(),
        is_active=True,
        priority=2
    )
    
    print(f'✓ Created emergency rule: {emergency_rule.name} (+{emergency_rule.adjustment_value}%)')
    print(f'✓ Created volume rule: {volume_rule.name} ({volume_rule.adjustment_value}%)')
    
    # Test 4: Create service bundles
    print('\n4. Creating service bundles...')
    
    if services.count() >= 2:
        # Calculate individual total first
        individual_total = sum(service.base_price for service in services[:2])

        # Create a comprehensive checkup bundle
        checkup_bundle = ServiceBundle.objects.create(
            name='Comprehensive Health Checkup',
            description='Complete health checkup package including consultation, basic tests, and follow-up',
            bundle_price=Decimal('250.00'),
            individual_total=individual_total,
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + timedelta(days=365),
            is_active=True,
            requires_approval=False
        )
        
        # Add services to bundle
        for i, service in enumerate(services[:2]):
            bundle_service = BundleService.objects.create(
                bundle=checkup_bundle,
                service=service,
                quantity=1,
                individual_price=service.base_price,
                is_required=True
            )
            print(f'  Added {service.name}: ${service.base_price}')

        # Calculate and update bundle savings
        checkup_bundle.calculate_savings()
        checkup_bundle.save()
        
        print(f'✓ Created bundle: {checkup_bundle.name}')
        print(f'  Bundle price: ${checkup_bundle.bundle_price}')
        print(f'  Individual total: ${checkup_bundle.individual_total}')
        print(f'  Savings: ${checkup_bundle.savings_amount} ({checkup_bundle.savings_percentage:.1f}%)')
    
    # Test 5: Test pricing analytics
    print('\n5. Testing pricing analytics...')
    
    # Service pricing statistics
    total_services = Service.objects.filter(is_active=True).count()
    total_pricing_tiers = PricingTier.objects.filter(is_active=True).count()
    total_service_pricing = ServicePricing.objects.filter(is_active=True).count()
    total_dynamic_rules = DynamicPricingRule.objects.filter(is_active=True).count()
    total_bundles = ServiceBundle.objects.filter(is_active=True).count()
    
    print(f'✓ Pricing system statistics:')
    print(f'  Active services: {total_services}')
    print(f'  Pricing tiers: {total_pricing_tiers}')
    print(f'  Service pricing records: {total_service_pricing}')
    print(f'  Dynamic pricing rules: {total_dynamic_rules}')
    print(f'  Service bundles: {total_bundles}')
    
    # Price range analysis
    if services.exists():
        service_prices = [service.base_price for service in services]
        min_price = min(service_prices)
        max_price = max(service_prices)
        avg_price = sum(service_prices) / len(service_prices)
        
        print(f'✓ Price range analysis:')
        print(f'  Minimum price: ${min_price}')
        print(f'  Maximum price: ${max_price}')
        print(f'  Average price: ${avg_price:.2f}')
    
    # Test 6: Service utilization analysis
    print('\n6. Service utilization analysis...')
    
    # Analyze service usage from invoice items
    service_usage = {}
    invoice_items = InvoiceItem.objects.all()
    
    for item in invoice_items:
        service_name = item.service.name
        if service_name not in service_usage:
            service_usage[service_name] = {
                'count': 0,
                'total_revenue': Decimal('0.00'),
                'avg_price': Decimal('0.00')
            }
        
        service_usage[service_name]['count'] += item.quantity
        service_usage[service_name]['total_revenue'] += item.total_price
    
    # Calculate averages
    for service_name, data in service_usage.items():
        if data['count'] > 0:
            data['avg_price'] = data['total_revenue'] / data['count']
    
    # Sort by usage count
    popular_services = sorted(
        service_usage.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )
    
    print(f'✓ Service utilization (top 5):')
    for service_name, data in popular_services[:5]:
        print(f'  {service_name}: {data["count"]} uses, ${data["total_revenue"]} revenue, ${data["avg_price"]:.2f} avg')
    
    # Test 7: Pricing tier effectiveness
    print('\n7. Pricing tier effectiveness...')
    
    tier_usage = {}
    for tier in PricingTier.objects.filter(is_active=True):
        pricing_count = ServicePricing.objects.filter(pricing_tier=tier, is_active=True).count()
        tier_usage[tier.name] = {
            'pricing_count': pricing_count,
            'discount_percentage': float(tier.discount_percentage),
            'tier_type': tier.tier_type
        }
    
    print(f'✓ Pricing tier usage:')
    for tier_name, data in tier_usage.items():
        print(f'  {tier_name}: {data["pricing_count"]} services, {data["discount_percentage"]}% discount')
    
    # Test 8: Bundle effectiveness
    print('\n8. Bundle effectiveness...')
    
    bundles = ServiceBundle.objects.filter(is_active=True)
    if bundles.exists():
        total_bundle_savings = sum(bundle.savings_amount for bundle in bundles)
        avg_savings_percentage = sum(bundle.savings_percentage for bundle in bundles) / bundles.count()
        
        print(f'✓ Bundle effectiveness:')
        print(f'  Total bundles: {bundles.count()}')
        print(f'  Total potential savings: ${total_bundle_savings}')
        print(f'  Average savings percentage: {avg_savings_percentage:.1f}%')
        
        for bundle in bundles:
            bundle_services_count = BundleService.objects.filter(bundle=bundle).count()
            print(f'  {bundle.name}: {bundle_services_count} services, ${bundle.savings_amount} savings')
    
    # Test 9: Dynamic pricing rule analysis
    print('\n9. Dynamic pricing rule analysis...')
    
    active_rules = DynamicPricingRule.objects.filter(is_active=True)
    print(f'✓ Active dynamic pricing rules: {active_rules.count()}')
    
    for rule in active_rules:
        affected_services = rule.services.count()
        affected_categories = rule.service_categories.count()
        print(f'  {rule.name}: {rule.adjustment_value}% adjustment, {affected_services} services, {affected_categories} categories')
    
    print('\n=== Pricing and Service Management System Testing Complete ===')

if __name__ == '__main__':
    test_pricing_management_system()
