# Hospital Management API

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/Django-5.2+-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django%20REST%20Framework-3.15+-orange.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive, production-ready Hospital Management System API built with Django REST Framework. This system provides complete healthcare facility management capabilities including patient care, appointment scheduling, medical records, billing, and administrative functions.

## 🏗️ Project Structure

```
HospitalManagementSystem/
├── 📁 accounts/              # User authentication & authorization
├── 📁 appointments/          # Appointment scheduling & management
├── 📁 billing/              # Billing & payment processing
├── 📁 data/                 # Database files (SQLite for development)
├── 📁 docs/                 # Project documentation
│   ├── 📁 generated/        # Auto-generated API documentation
│   └── 📁 testing/          # Testing guides and documentation
├── 📁 doctors/              # Doctor profiles & management
├── 📁 hospital_backend/     # Django project settings & configuration
├── 📁 infrastructure/       # Infrastructure & system management
├── 📁 logs/                 # Application logs
├── 📁 media/                # User uploaded files
├── 📁 medical_records/      # Electronic Health Records (EHR)
├── 📁 notifications/        # Notification system
├── 📁 patients/             # Patient profiles & management
├── 📁 scripts/              # Utility scripts & automation
└── 📁 tests/                # Test suites & validation
    ├── 📁 demo/             # Demo & example tests
    ├── 📁 legacy/           # Legacy test files
    ├── 📁 management/       # Django management command tests
    └── 📁 validation/       # Feature validation tests
```

## 🏥 Features

### Core Management Systems
- **👥 Patient Management**: Complete patient lifecycle management with medical history tracking
- **👨‍⚕️ Doctor Management**: Doctor profiles, specializations, schedules, and availability
- **📅 Appointment System**: Advanced scheduling with conflict detection and automated reminders
- **📋 Medical Records**: Electronic Health Records (EHR) with secure document management
- **💰 Billing & Invoicing**: Comprehensive billing system with insurance claim processing
- **🏢 Infrastructure Management**: Hospital facilities, departments, and equipment tracking

### Advanced Features
- **🔐 Role-Based Access Control (RBAC)**: Secure multi-role authentication system
- **📧 Notification System**: Email, SMS, and push notifications with template management
- **📊 Analytics & Reporting**: Comprehensive reporting and dashboard analytics
- **🔍 Advanced Search & Filtering**: Powerful search capabilities across all modules
- **📱 API Documentation**: Interactive Swagger/OpenAPI documentation
- **⚡ Performance Optimized**: Redis caching, database optimization, and monitoring

## � Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7.0+ (optional, for caching)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/hospital-management-api.git
   cd hospital-management-api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv hospital_env
   source hospital_env/bin/activate  # On Windows: hospital_env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database Setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run the server**
   ```bash
   python manage.py runserver
   ```

7. **Access the API**
   - API Base URL: `http://localhost:8000/api/`
   - Admin Panel: `http://localhost:8000/admin/`
   - API Documentation: `http://localhost:8000/api/docs/`

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

### Core Endpoints

#### Authentication
```
POST /api/accounts/auth/login/          # User login
POST /api/accounts/auth/refresh/        # Token refresh
POST /api/accounts/auth/logout/         # User logout
POST /api/accounts/register/            # User registration
```

#### Patient Management
```
GET    /api/patients/                   # List patients
POST   /api/patients/                   # Create patient
GET    /api/patients/{id}/              # Patient details
PUT    /api/patients/{id}/              # Update patient
DELETE /api/patients/{id}/              # Delete patient
```

#### Appointment Management
```
GET    /api/appointments/               # List appointments
POST   /api/appointments/               # Create appointment
GET    /api/appointments/{id}/          # Appointment details
PUT    /api/appointments/{id}/          # Update appointment
DELETE /api/appointments/{id}/          # Cancel appointment
```

#### Medical Records
```
GET    /api/medical-records/            # List medical records
POST   /api/medical-records/            # Create record
GET    /api/medical-records/{id}/       # Record details
PUT    /api/medical-records/{id}/       # Update record
```

#### Billing System
```
GET    /api/billing/invoices/           # List invoices
POST   /api/billing/invoices/           # Create invoice
GET    /api/billing/invoices/{id}/      # Invoice details
POST   /api/billing/payments/           # Process payment
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=hospital_management_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Security
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440

# Redis Configuration (Optional)
USE_REDIS=True
REDIS_URL=redis://localhost:6379/1

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Database Setup

#### PostgreSQL (Recommended)
```sql
CREATE DATABASE hospital_management_db;
CREATE USER hospital_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE hospital_management_db TO hospital_user;
```

#### Neon PostgreSQL (Cloud)
```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=hospital_management_db
DB_USER=hospital_management_db_owner
DB_PASSWORD=your_neon_password
DB_HOST=ep-dawn-base-a8jdmrnf-pooler.eastus2.azure.neon.tech
DB_PORT=5432
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test patients

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html

# Legacy test scripts
python scripts/run_tests.py
python scripts/run_integration_tests.py
python scripts/run_performance_tests.py
```

## 🏗️ Architecture

### Technology Stack
- **Backend Framework**: Django 5.2+ with Django REST Framework
- **Database**: PostgreSQL with optimized queries
- **Caching**: Redis for session management and API caching
- **Authentication**: JWT-based authentication with role-based access
- **Documentation**: drf-spectacular for OpenAPI/Swagger docs
- **Monitoring**: Comprehensive logging and performance monitoring

### Project Structure
```
hospital-management-api/
├── accounts/              # User management and authentication
├── patients/              # Patient management system
├── doctors/               # Doctor profiles and management
├── appointments/          # Appointment scheduling system
├── medical_records/       # Electronic health records
├── billing/               # Billing and payment processing
├── notifications/         # Notification system
├── infrastructure/        # Hospital infrastructure management
├── hospital_backend/      # Core Django settings and configuration
├── tests/                 # Comprehensive test suite
├── docs/                  # Additional documentation
├── scripts/               # Utility scripts
└── requirements.txt       # Python dependencies
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: Fine-grained permissions system
- **Rate Limiting**: API endpoint protection against abuse
- **Input Validation**: Comprehensive data validation and sanitization
- **Security Headers**: CORS, CSP, and other security headers
- **Audit Logging**: Complete audit trail for all operations
- **Data Encryption**: Sensitive data encryption at rest

## 📊 Performance Features

- **Database Optimization**: Optimized queries with select_related/prefetch_related
- **Redis Caching**: Multi-level caching strategy for improved performance
- **Connection Pooling**: Efficient database connection management
- **Response Compression**: GZip compression for reduced bandwidth
- **Performance Monitoring**: Real-time performance metrics and alerting

## 📦 Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   # Set production environment variables
   export DEBUG=False
   export USE_REDIS=True
   export ALLOWED_HOSTS=yourdomain.com
   ```

2. **Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Database Migration**
   ```bash
   python manage.py migrate
   ```

4. **WSGI Server** (Gunicorn recommended)
   ```bash
   pip install gunicorn
   gunicorn hospital_backend.wsgi:application --bind 0.0.0.0:8000
   ```

### Docker Deployment

```dockerfile
# Dockerfile included in repository
docker build -t hospital-management-api .
docker run -p 8000:8000 hospital-management-api
```

### Cloud Deployment
- **Heroku**: Ready for Heroku deployment
- **AWS**: Compatible with AWS ECS/EKS
- **DigitalOcean**: App Platform ready
- **Railway**: One-click deployment support

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [API Documentation](http://localhost:8000/api/docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/hospital-management-api/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/hospital-management-api/discussions)

## 🙏 Acknowledgments

- Django and Django REST Framework communities
- Healthcare industry standards and best practices
- Open source contributors and maintainers

---

**Built with ❤️ for healthcare professionals worldwide**
