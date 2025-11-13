"""
Django management command to create test project entries for development.
This script creates 10 random project entries with images from picsum.photos
"""
import random
import tempfile
import os
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from django.core.management.base import BaseCommand
from django.core.files import File
from homepage.models import Project


class Command(BaseCommand):
    help = 'Creates 10 random test project entries with images from picsum.photos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of projects to create (default: 10)',
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Sample data for random generation
        project_titles = [
            "E-Commerce Platform",
            "Task Management App",
            "Social Media Dashboard",
            "Weather Forecast API",
            "Recipe Sharing Website",
            "Fitness Tracker",
            "Music Player",
            "Blog CMS",
            "Chat Application",
            "Analytics Dashboard",
            "Photo Gallery",
            "Event Management System",
            "Learning Management System",
            "Inventory Tracker",
            "Booking System",
        ]
        
        project_types = [
            "Web Development Django",
            "Full Stack React",
            "Mobile App Flutter",
            "API REST",
            "Machine Learning",
            "Data Science Python",
            "DevOps Docker",
            "Frontend JavaScript",
            "Backend Python",
            "Cloud AWS",
        ]
        
        descriptions = [
            "A comprehensive platform built with modern web technologies.",
            "An intuitive application designed for seamless user experience.",
            "A powerful tool that simplifies complex workflows.",
            "A scalable solution for managing large datasets.",
            "An innovative project showcasing cutting-edge technology.",
            "A user-friendly interface with robust backend architecture.",
            "A responsive design optimized for all devices.",
            "A secure application with advanced authentication features.",
            "A high-performance system with real-time capabilities.",
            "An elegant solution to everyday problems.",
        ]
        
        github_links = [
            "https://github.com/user/project1",
            "https://github.com/user/project2",
            "https://github.com/user/project3",
            "https://github.com/user/project4",
            "https://github.com/user/project5",
        ]
        
        demo_links = [
            "https://demo.example.com/project1",
            "https://demo.example.com/project2",
            "https://demo.example.com/project3",
            "https://demo.example.com/project4",
            "https://demo.example.com/project5",
        ]

        self.stdout.write(f'Creating {count} test project entries...')

        for i in range(count):
            # Generate random data
            title = random.choice(project_titles)
            if random.random() > 0.3:  # 70% chance to have a number
                title = f"{title} {random.randint(1, 100)}"
            
            description = random.choice(descriptions)
            project_type = random.choice(project_types)
            
            # Randomly assign links (some projects might not have them)
            github_link = random.choice(github_links) if random.random() > 0.2 else None
            link = random.choice(demo_links) if random.random() > 0.3 else None

            # Download image from picsum.photos
            image_url = "https://picsum.photos/200"
            try:
                # Download image using urllib (built-in, no extra dependency)
                with urlopen(image_url, timeout=10) as response:
                    image_data = response.read()
                
                # Create a temporary file to save the image
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                    tmp_file.write(image_data)
                    tmp_file_path = tmp_file.name
                
                # Create the project
                project = Project(
                    title=title,
                    description=description,
                    type=project_type,
                    github_link=github_link,
                    link=link,
                )
                
                # Save the image to the project
                with open(tmp_file_path, 'rb') as img_file:
                    project.image.save(
                        f'test_project_{i+1}.jpg',
                        File(img_file),
                        save=False
                    )
                
                project.save()
                
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created project: {title}')
                )
                
            except (URLError, HTTPError) as e:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ Failed to download image for "{title}": {e}. Creating project without image.'
                    )
                )
                # Create project without image
                project = Project(
                    title=title,
                    description=description,
                    type=project_type,
                    github_link=github_link,
                    link=link,
                )
                project.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created project (no image): {title}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error creating project "{title}": {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully created {count} test project entries!')
        )

