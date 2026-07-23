# AutoCare Pro Midterm Demo Script

## Opening hook

Hello everyone, my project is AutoCare Pro, a vehicle maintenance and service tracker. The tagline is: "Never miss another maintenance appointment."

## Problem statement

Many vehicle owners forget routine maintenance like oil changes, tire rotations, registration renewals, and inspection dates. These small missed tasks can turn into expensive repairs. AutoCare Pro solves this by giving users one simple dashboard for storing vehicle information and tracking maintenance history.

## User persona

My user persona is Khalil Sobeh, a 24-year-old vehicle owner in Jordan who drives daily. He wants a simple way to remember maintenance dates and keep his service history organized. His frustrations directly shaped the dashboard and add-vehicle feature I am demonstrating today.

## Live prototype demonstration

For the vertical slice, I built the core feature where a user can add a vehicle and see it saved to the dashboard.

1. Open the browser at `http://127.0.0.1:5000`.
2. Register an account or log in.
3. Go to the dashboard.
4. Fill out the Add Vehicle form.
5. Click Add Vehicle.
6. Show that the dashboard updates with the new vehicle.
7. Click Refresh API to show the frontend can read the saved vehicle data from the backend.

## Code architecture highlight

In `app.py`, the `/vehicles/add` route receives form data from the UI, validates it, writes it into the SQLite vehicles table, and redirects back to the dashboard. The dashboard route reads all vehicles for the logged-in user and displays them in the interface.

## Roadmap

The next three major features are:

1. Add maintenance records for each vehicle.
2. Add reminder logic for oil changes and inspections.
3. Add receipt uploads and maintenance cost summaries.

## Closing

AutoCare Pro is currently a working vertical slice, but the architecture is ready to expand into a complete vehicle maintenance platform.
