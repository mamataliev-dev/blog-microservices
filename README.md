# 🚀 User Service for Blog Microservices

## 🌟 Overview
The **User Service** is a core component of the Blog Microservices project. It handles user authentication, authorization, and management while exposing a **RESTful API** for seamless interaction with other services using **gRPC**.

---

## 🎯 Features
✅ **User Data Management** – Create, read, update, and delete user profiles.  
✅ **Authentication & Authorization** – Secure login & token-based authentication.  
✅ **RESTful API** – Standard API endpoints for user operations.  
✅ **gRPC Communication** – High-performance inter-service communication.  
✅ **Caching** – Redis integration for enhanced performance.  
✅ **Unit Testing** – Comprehensive test coverage for API & gRPC functionalities.  

---

## 🛠 Tech Stack
- **Python & Flask** – For building the RESTful API.
- **PostgreSQL** – Relational database for user data storage.
- **Redis** – Caching for faster access and improved performance.
- **gRPC** – Efficient microservice communication.
- **Testing** – Unit tests using `pytest`.

---

## 🔧 Installation & Setup

### 📥 Clone the Repository
```bash
git clone https://github.com/mamataliev-dev/blog-microservices.git
cd blog-microservices/UserService
```
### 🏗 Set Up a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
### 📦 Install Dependencies
```bash
pip install -r requirements.txt
```
---

## 🗄 Database Setup
1. Ensure PostgreSQL is installed and running.
2. Create a database for the User Service:

   ``` sql
   CREATE DATABASE userservice;
   ```
3. Update the database connection settings in `config.py`:
   
   ``` sql
   SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost:5432/userservice'
   ```
---

## ⚡️ Redis Setup
1. Install and start Redis:
   - macOS:  

     ``` bash
     brew install redis && redis-server
     ```
   - Ubuntu:  
    
     ``` bash
     sudo apt install redis-server && redis-server
     ```
    - Windows: Use WSL or download Redis binaries.
2. Update Redis connection settings in config.py:
   
   ``` bash
   REDIS_HOST = 'localhost'
   REDIS_PORT = 6379
   ```
   
---

## ⚙️ Configuration
Customize settings via environment variables or `config.py`:
- Database URL: PostgreSQL connection string (e.g., `postgresql://user:pass@localhost:5432/userservice`).

- Redis Host & Port: Set Redis connection details (e.g., `localhost:6379`).
- gRPC Settings: Define endpoints and credentials for service communication.

---

## 🚀 Running the Service
Start the Flask server:
```python
python run.py
```
The service will be available at `http://localhost:5000` (or as defined in your config).

---

## 🔗 gRPC Integration
This service leverages gRPC for microservice communication. 
Protocol buffer definitions are located in the proto/ directory. 
Refer to `user_service.py` for setup details.

---