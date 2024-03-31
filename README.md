# YouTube Clone App

This is a YouTube clone application backend built using Django, Firestore, Docker and PostgreSQL. The application backend provides the basis with which the frontend allows users to upload, view, like, and comment on videos, similar to the functionality provided by YouTube.

## Features

- User authentication: Users can sign up, sign in, and sign out securely.
- Video uploading: Users can upload videos to share with others.
- Video viewing: Users can browse and watch videos uploaded by other users.
- Like and comment: Users can like and comment on videos to engage with the content and other users.
- Search functionality: Users can search for videos based on keywords or categories.

## Technologies Used

- Django: Backend framework for building RESTful APIs and handling user authentication.
- Firestore: Cloud-based NoSQL database for storing user data and video metadata.
- Firebase Authentication: Used for user authentication and authorization.
- Docker: Deployment, containerization.
- PostgreSQL: Relational database management system for storing video content and relational data.

## Getting Started

### Prerequisites

- Python and pip installed on your machine for running the Django backend.
- Firebase account and Firestore set up for storing user data.
- PostgreSQL database set up for storing video content.
- Docker installed and set-up.

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/malezubky/ytb_clone_backend.git
   ```

2. Navigate to the project directory:

   ```bash
   cd ytb_clone_backend
   ```

4. Install backend dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Set up Firebase Firestore:
   - Create a Firebase project and set up Firestore.
   - Copy the Firebase configuration details into your backend settings.
   - Ensure Firestore rules allow read and write access as required.

6. Set up PostgreSQL:
   - Create a PostgreSQL database.
   - Configure the backend to connect to your PostgreSQL database.

7. Start the backend server:

   ```bash
   # In the backend directory
   python manage.py runserver
   ```

8. Access the application in your web browser:

   ```
   http://localhost8000
   ```

## License

This project is licensed under the MIT License

## Acknowledgments

- This project was inspired by the functionality provided by YouTube.
- Special thanks to the developers of React, Django, Firestore, Docker and PostgreSQL for their amazing tools and documentation.
- Thanks to the open-source community for providing helpful resources and tutorials.
