from django.shortcuts import render


def documentation_home(request):
    """
    Render the main documentation page with links to all documentation resources.
    """
    context = {
        'title': 'Hospital Management System API Documentation',
        'version': '1.0.0',
        'description': 'Comprehensive API documentation for the Hospital Management System'
    }
    return render(request, 'docs/home.html', context)
