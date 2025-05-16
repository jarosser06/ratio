"""
Simple script authored by AI, that clears out an ECR repository of images that are older
than a day. Helpful to keep ECR costs low
"""

import boto3
from datetime import datetime, timedelta, timezone


def find_old_ecr_images(max_age_days=1):
    """
    Find all ECR images older than specified days across all repositories
    
    Args:
        max_age_days (int): Maximum age in days, default is 1 day
    
    Returns:
        dict: Dictionary with repository names as keys and lists of old image details as values
    """
    # Initialize ECR client
    ecr_client = boto3.client('ecr')
    
    # Calculate the cutoff time
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    
    # Get list of all repositories
    repositories = []
    paginator = ecr_client.get_paginator('describe_repositories')
    for page in paginator.paginate():
        repositories.extend(page['repositories'])
    
    # Dictionary to store results
    old_images = {}
    
    # Check each repository for old images
    for repo in repositories:
        repo_name = repo['repositoryName']
        print(f"Checking repository: {repo_name}")
        
        old_images_in_repo = []
        
        # Use pagination to handle repositories with many images
        image_paginator = ecr_client.get_paginator('describe_images')
        for image_page in image_paginator.paginate(repositoryName=repo_name):
            for image in image_page['imageDetails']:
                # Check if image is older than cutoff
                push_date = image.get('imagePushedAt')
                if push_date and push_date < cutoff_time:
                    old_images_in_repo.append({
                        'imageDigest': image['imageDigest'],
                        'imageTags': image.get('imageTags', []),
                        'imagePushedAt': push_date,
                        'imageSizeInBytes': image.get('imageSizeInBytes', 'N/A')
                    })
        
        if old_images_in_repo:
            old_images[repo_name] = old_images_in_repo
            print(f"  Found {len(old_images_in_repo)} image(s) older than {max_age_days} day(s)")
        else:
            print(f"  No images older than {max_age_days} day(s) found")
    
    return old_images

def delete_old_ecr_images(old_images, dry_run=True):
    """
    Delete old ECR images based on the output from find_old_ecr_images
    
    Args:
        old_images (dict): Dictionary with repository names as keys and lists of old image details as values
        dry_run (bool): If True, only simulate deletion without actually deleting
    
    Returns:
        dict: Dictionary with repository names as keys and lists of deleted image details as values
    """
    ecr_client = boto3.client('ecr')
    deleted_images = {}
    
    mode = "DRY RUN" if dry_run else "DELETION"
    print(f"\n{mode} MODE: {'Simulating' if dry_run else 'Performing'} deletion of old ECR images")
    
    for repo_name, images in old_images.items():
        print(f"\nRepository: {repo_name}")
        deleted_in_repo = []
        
        # ECR batch delete can handle up to 100 images at a time
        batch_size = 100
        image_batches = [images[i:i+batch_size] for i in range(0, len(images), batch_size)]
        
        for batch in image_batches:
            image_ids = []
            for image in batch:
                # Add digest-based identifier (required)
                image_id = {'imageDigest': image['imageDigest']}
                image_ids.append(image_id)
                
                # For logging purposes
                tags = ", ".join(image.get('imageTags', ['<untagged>']))
                push_date = image['imagePushedAt'].strftime('%Y-%m-%d %H:%M:%S UTC')
                print(f"  Deleting: {image['imageDigest'][:12]}... (Tags: {tags}, Pushed: {push_date})")
            
            if not dry_run:
                try:
                    response = ecr_client.batch_delete_image(
                        repositoryName=repo_name,
                        imageIds=image_ids
                    )
                    
                    # Handle successful deletions
                    if 'imageIds' in response:
                        deleted_in_repo.extend(batch[:len(response['imageIds'])])
                    
                    # Handle failed deletions
                    if 'failures' in response and response['failures']:
                        print("  Some images failed to delete:")
                        for failure in response['failures']:
                            print(f"    {failure.get('imageId', {}).get('imageDigest', 'Unknown')} - {failure.get('failureReason', 'Unknown reason')}")
                
                except Exception as e:
                    print(f"  Error deleting images: {str(e)}")
            else:
                # In dry run mode, just simulate successful deletion
                deleted_in_repo.extend(batch)
        
        if deleted_in_repo:
            deleted_images[repo_name] = deleted_in_repo
            print(f"  {len(deleted_in_repo)} image(s) {'would be' if dry_run else 'were'} deleted from {repo_name}")
    
    # Print summary
    total_deleted = sum(len(images) for images in deleted_images.values())
    print(f"\n{mode} SUMMARY: {total_deleted} image(s) {'would be' if dry_run else 'were'} deleted across {len(deleted_images)} repositories")
    
    return deleted_images

def main():
    # Find images older than 1 day
    old_images = find_old_ecr_images()
    
    if not old_images:
        print("No old images found to delete.")
        return
    
    # Ask for confirmation before actual deletion
    confirmation = input("\nDo you want to delete these images? [y/N]: ").lower()
    
    if confirmation == 'y':
        # Perform actual deletion
        delete_old_ecr_images(old_images, dry_run=False)
    else:
        print("Deletion canceled.")

if __name__ == "__main__":
    main()
