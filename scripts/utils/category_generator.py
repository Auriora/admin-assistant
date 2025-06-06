#!/usr/bin/env python3
"""
Category generator for creating test categories in Outlook.
"""
import asyncio
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.models.user import User
from core.repositories.user_repository import SQLAlchemyUserRepository
from core.repositories.category_repository_msgraph import MSGraphCategoryRepository
from core.db import SessionLocal


class CategoryGenerator:
    """Generates standard test categories for appointment testing."""
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.stats = {
            'created': 0,
            'existing': 0,
            'categories': []
        }
    
    def generate_categories(self, dry_run: bool = False) -> Dict[str, Any]:
        """Generate standard test categories."""
        return asyncio.run(self._generate_categories_async(dry_run))
    
    async def _generate_categories_async(self, dry_run: bool = False) -> Dict[str, Any]:
        """Async implementation of category generation."""
        # Get user and repository
        session = SessionLocal()
        try:
            user_repo = SQLAlchemyUserRepository(session)
            user = user_repo.get_by_email(self.user_email)
            
            if not user:
                raise ValueError(f"User not found: {self.user_email}")
            
            # Note: We'll need to implement MSGraph category creation
            # For now, we'll create the category list that should be created
            
            categories = self._get_standard_categories()
            
            if dry_run:
                print(f"Would create {len(categories)} categories:")
                for category in categories:
                    print(f"  • {category}")
                self.stats['categories'] = categories
                return self.stats
            
            # TODO: Implement actual category creation via MSGraph
            # This would require extending the MSGraphCategoryRepository
            print("Category creation via MSGraph not yet implemented.")
            print("Categories that should be created:")
            for category in categories:
                print(f"  • {category}")
            
            self.stats['categories'] = categories
            self.stats['created'] = len(categories)
            
            return self.stats
            
        finally:
            session.close()
    
    def _get_standard_categories(self) -> List[str]:
        """Get the list of standard test categories."""
        categories = []
        
        # Customer-based categories (billable)
        customers_billable = [
            "Acme Corp",
            "TechStart Inc", 
            "Global Solutions",
            "Modena",
            "Innovation Labs",
            "Digital Dynamics",
            "Future Systems",
            "Smart Solutions",
            "Enterprise Plus",
            "NextGen Tech"
        ]
        
        # Customer-based categories (non-billable)
        customers_non_billable = [
            "Acme Corp",
            "TechStart Inc",
            "Internal Project",
            "Research Initiative",
            "Community Outreach"
        ]
        
        # Add billable categories
        for customer in customers_billable:
            categories.append(f"Billable - {customer}")
        
        # Add non-billable categories  
        for customer in customers_non_billable:
            categories.append(f"Non-billable - {customer}")
        
        # Add special categories
        special_categories = [
            "Admin - non-billable",
            "Break - non-billable", 
            "Online"
        ]
        categories.extend(special_categories)
        
        # Add some alternative format categories (for testing flexibility)
        alternative_format = [
            "Consulting - Acme Corp",
            "Development - TechStart Inc",
            "Support - Global Solutions"
        ]
        categories.extend(alternative_format)
        
        return sorted(categories)


if __name__ == "__main__":
    # Test the generator
    generator = CategoryGenerator("test@example.com")
    result = generator.generate_categories(dry_run=True)
    print(f"Generated {len(result['categories'])} categories")
