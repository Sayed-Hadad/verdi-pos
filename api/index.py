# Vercel Python Serverless entry wrapping Flask as ASGI
from asgiref.wsgi import WsgiToAsgi
from app import create_app

# Create the original Flask WSGI app
_flask_app = create_app()

# Export ASGI app for Vercel runtime detection
app = WsgiToAsgi(_flask_app)
