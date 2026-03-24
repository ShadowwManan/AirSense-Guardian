# Author: Daksha009
# Repo: https://github.com/Daksha009/AirSense-Guardian.git

"""
Simple HTTP server to serve the frontend HTML file
"""
import http.server
import socketserver
import os
import sys

PORT = 3000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        # Serve index.html for root path
        if self.path == '/':
            self.path = '/index.html'
            
        # Extract the local file path (remove leading slash or query params if any)
        local_path = self.path.lstrip('/').split('?')[0]
        
        # If the file doesn't exist and it's not an API or static API route, serve index.html
        if local_path and not os.path.exists(local_path) and not self.path.startswith('/api'):
            self.path = '/index.html'
            
        return super().do_GET()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Frontend server running at http://localhost:{PORT}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")

