# Savory

A comprehensive recipe management and meal planning platform that helps home cooks discover, organize, and prepare meals efficiently.

## Project Overview

Savory is a Django-based web application that provides a complete solution for recipe management, ingredient tracking, and meal planning. The platform helps users organize their recipes, manage their pantry, create shopping lists, and discover new recipes based on available ingredients.

### Key Features

1. **Recipe Management**

    - Detailed recipe information including prep time, cook time, and total time
    - Comprehensive nutritional information (calories, macronutrients, etc.)
    - Step-by-step cooking instructions
    - Multiple recipe images with carousel support
    - Recipe categorization and tagging system
    - User recipe collections for saving favorites

2. **Pantry Management**

    - Track ingredients in your pantry
    - Associate related ingredients
    - Monitor ingredient usage and expiration

3. **Shopping List**

    - Create and manage shopping lists
    - Check off items as you shop
    - Alphabetical organization of ingredients
    - Easy addition of ingredients from recipes

4. **User Features**
    - User authentication and profiles
    - Personal recipe collections
    - Customizable shopping lists
    - Personalized pantry management

## Technical Stack

-   **Backend**: Python with Django framework
-   **Database**: SQLite (development)
-   **Frontend**: HTML, CSS, JavaScript, Bootstrap
-   **Development Environment**: Visual Studio Code
-   **Server**: Django development server (Development)

## Project Structure

```
savory/
├── manage.py
├── requirements.txt
├── Procfile
├── savory/              # Main project directory
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── apps/               # Application modules
    ├── recipes/        # Recipe management and discovery
    ├── users/          # User profiles and authentication
    ├── pantry/         # Pantry management
    └── shopping/       # Shopping list functionality
```

## Getting Started

### Prerequisites

-   Python 3.x
-   Django
-   Modern web browser

### Installation

1. Clone the repository
2. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Run database migrations:
    ```bash
    python manage.py migrate
    ```
5. Start the development server:
    ```bash
    python manage.py runserver
    ```

## Development

The project follows Django's best practices for project structure and organization. Each app is responsible for a specific feature set:

-   **recipes**: Handles recipe management, including models for recipes, ingredients, steps, and images
-   **users**: Manages user authentication and profiles
-   **pantry**: Tracks user's pantry items and ingredient relationships
-   **shopping**: Manages shopping lists and item tracking
