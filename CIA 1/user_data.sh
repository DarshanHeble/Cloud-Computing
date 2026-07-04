#!/bin/bash
# Update package list and upgrade packages
apt-get update -y

# Install Apache2
apt-get install apache2 -y

# Enable and start Apache service
systemctl enable apache2
systemctl start apache2

# Write custom HTML page displaying Name and Register Number
cat <<EOF > /var/www/html/index.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloud CIA 1 Portal</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            text-align: center;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            padding: 3rem;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        h1 {
            margin-bottom: 0.5rem;
            font-size: 2.5rem;
            background: linear-gradient(to right, #3b82f6, #60a5fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p {
            font-size: 1.25rem;
            margin: 0.5rem 0;
            color: #cbd5e1;
        }
        .highlight {
            font-weight: bold;
            color: #3b82f6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Cloud Computing CIA 1</h1>
        <p>Candidate Name: <span class="highlight">Darshan</span></p>
        <p>Register Number: <span class="highlight">2547119</span></p>
        <p>Status: Apache Web Server Running Successfully</p>
    </div>
</body>
</html>
EOF
