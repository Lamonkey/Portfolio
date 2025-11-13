# Create Test Projects Management Command

## Overview

The `create_test_projects` command is a Django management command designed for development and testing purposes. It automatically generates random project entries in your database with sample data, including images downloaded from [Picsum Photos](https://picsum.photos/).

## Purpose

This command is useful for:
- **Development Testing**: Quickly populate your database with sample projects to test UI/UX
- **Demo Data**: Create realistic-looking project entries for demonstrations
- **Development Workflow**: Speed up development by avoiding manual data entry

## Requirements

Before using this command, ensure you have:

1. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```
   The command requires the `requests` library (already included in `requirements.txt`).

2. **Database configured**: Your Django project should have a properly configured database (SQLite, PostgreSQL, etc.)

3. **Media settings**: Ensure your Django `MEDIA_ROOT` and `MEDIA_URL` settings are configured if you want images to be stored properly.

## Usage

### Basic Usage

Run the command from your project's `src` directory:

```bash
cd src
python manage.py create_test_projects
```

This will create **10 test project entries** by default.

### Custom Count

To create a different number of projects, use the `--count` option:

```bash
python manage.py create_test_projects --count 20
```

This will create 20 project entries instead of the default 10.

### Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--count` | Integer | 10 | Number of project entries to create |

## What Gets Created

Each project entry includes:

- **Title**: Randomly selected from a predefined list of project titles (e.g., "E-Commerce Platform", "Task Management App")
- **Description**: Randomly selected from a list of sample descriptions
- **Type**: Randomly selected project type (e.g., "Web Development Django", "Full Stack React")
- **Image**: Downloaded from `https://picsum.photos/200` (200x200px random image)
- **GitHub Link**: Randomly assigned GitHub link (70% chance of being assigned)
- **Demo Link**: Randomly assigned demo/project link (70% chance of being assigned)

### Sample Project Types

The command randomly assigns one of these project types:
- Web Development Django
- Full Stack React
- Mobile App Flutter
- API REST
- Machine Learning
- Data Science Python
- DevOps Docker
- Frontend JavaScript
- Backend Python
- Cloud AWS

## Output

The command provides real-time feedback as it creates projects:

```
Creating 10 test project entries...
✓ Created project: E-Commerce Platform 42
✓ Created project: Task Management App
✓ Created project: Social Media Dashboard 15
...
Successfully created 10 test project entries!
```

### Error Handling

The command handles errors gracefully:

- **Image Download Failures**: If an image cannot be downloaded, the project will still be created without an image, and a warning message will be displayed:
  ```
  ⚠ Failed to download image for "Project Title": [error]. Creating project without image.
  ✓ Created project (no image): Project Title
  ```

- **Other Errors**: If any other error occurs during project creation, an error message will be displayed, and the command will continue with the next project.

## Examples

### Create 10 Default Projects

```bash
cd src
python manage.py create_test_projects
```

### Create 5 Projects for Quick Testing

```bash
cd src
python manage.py create_test_projects --count 5
```

### Create 50 Projects for Load Testing

```bash
cd src
python manage.py create_test_projects --count 50
```

## File Structure

The command is located at:
```
src/homepage/management/commands/create_test_projects.py
```

This follows Django's standard management command structure:
```
app_name/
    management/
        __init__.py
        commands/
            __init__.py
            create_test_projects.py
```

## Troubleshooting

### Issue: Command Not Found

**Error**: `Unknown command: 'create_test_projects'`

**Solution**: 
- Ensure you're running the command from the `src` directory
- Verify the management command structure exists: `src/homepage/management/commands/create_test_projects.py`
- Check that `homepage` is listed in `INSTALLED_APPS` in your Django settings

### Issue: Image Download Fails

**Error**: `⚠ Failed to download image for "Project Title": [error]`

**Possible Causes**:
- No internet connection
- Picsum Photos service is down
- Network timeout

**Solution**: 
- Check your internet connection
- The command will continue and create projects without images
- You can manually add images later through the Django admin

### Issue: Permission Errors

**Error**: Permission denied when saving images

**Solution**:
- Ensure the `MEDIA_ROOT` directory exists and is writable
- Check file system permissions
- Verify Django media settings in `settings.py`

### Issue: Database Errors

**Error**: Database-related errors during project creation

**Solution**:
- Ensure migrations are up to date: `python manage.py migrate`
- Verify database connection settings
- Check that the `Project` model is properly defined

## Integration with Django Admin

After running the command, you can view and manage the created projects through the Django admin interface (if the `Project` model is registered in `admin.py`).

## Cleaning Up Test Data

To remove test projects created by this command, you can:

1. **Via Django Admin**: Delete projects individually through the admin interface
2. **Via Django Shell**:
   ```python
   python manage.py shell
   ```
   ```python
   from homepage.models import Project
   # Delete all projects (use with caution!)
   Project.objects.all().delete()
   # Or delete specific projects by filtering
   Project.objects.filter(title__icontains='test').delete()
   ```

## Notes

- **Random Data**: The command uses random selection, so each run will create different project entries
- **Image URLs**: Images are downloaded from Picsum Photos, which provides random placeholder images
- **Development Only**: This command is intended for development/testing environments. Use caution in production
- **No Duplicate Prevention**: The command does not check for existing projects, so running it multiple times will create duplicate entries

## Related Files

- **Model**: `src/homepage/models.py` - Defines the `Project` model
- **Views**: `src/homepage/views.py` - Displays projects in the software log
- **Templates**: `src/homepage/templates/homepage/software_log.html` - Template for displaying projects

## Support

For issues or questions about this command, refer to:
- Django Management Commands Documentation: https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
- Project README: `README.md`

