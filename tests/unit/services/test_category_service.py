"""
Unit tests for CategoryService

Tests the business logic for managing Category entities including
validation, CRUD operations, and duplicate checking.
"""

import pytest
from unittest.mock import Mock
from core.services.category_service import CategoryService
from core.models.category import Category
from core.repositories.category_repository_base import BaseCategoryRepository


class TestCategoryService:
    """Test suite for CategoryService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_repository = Mock(spec=BaseCategoryRepository)
        self.service = CategoryService(repository=self.mock_repository)
    
    def test_init_with_repository(self):
        """Test service initialization with repository"""
        service = CategoryService(repository=self.mock_repository)
        assert service.repository == self.mock_repository
    
    def test_get_by_id(self):
        """Test retrieving category by ID"""
        # Arrange
        category_id = "cat-123"
        expected_category = Mock(spec=Category)
        self.mock_repository.get_by_id.return_value = expected_category
        
        # Act
        result = self.service.get_by_id(category_id)
        
        # Assert
        assert result == expected_category
        self.mock_repository.get_by_id.assert_called_once_with(category_id)
    
    def test_get_by_id_not_found(self):
        """Test retrieving non-existent category"""
        # Arrange
        category_id = "nonexistent"
        self.mock_repository.get_by_id.return_value = None
        
        # Act
        result = self.service.get_by_id(category_id)
        
        # Assert
        assert result is None
        self.mock_repository.get_by_id.assert_called_once_with(category_id)
    
    def test_create_valid_category(self):
        """Test creating a valid category"""
        # Arrange
        category = Mock(spec=Category)
        category.name = "Test Category"
        category.user_id = 123
        
        # Mock repository methods for validation
        self.mock_repository.get_by_name.return_value = None  # No duplicate
        
        # Act
        self.service.create(category)
        
        # Assert
        self.mock_repository.get_by_name.assert_called_once_with("Test Category")
        self.mock_repository.add.assert_called_once_with(category)
    
    def test_create_invalid_category_empty_name(self):
        """Test creating category with empty name"""
        # Arrange
        category = Mock(spec=Category)
        category.name = ""
        category.user_id = 123
        
        # Act & Assert
        with pytest.raises(ValueError, match="Category name is required"):
            self.service.create(category)
        
        self.mock_repository.add.assert_not_called()
    
    def test_create_invalid_category_whitespace_name(self):
        """Test creating category with whitespace-only name"""
        # Arrange
        category = Mock(spec=Category)
        category.name = "   "
        category.user_id = 123
        
        # Act & Assert
        with pytest.raises(ValueError, match="Category name is required"):
            self.service.create(category)
        
        self.mock_repository.add.assert_not_called()
    
    def test_create_invalid_category_no_user_id(self):
        """Test creating category without user ID"""
        # Arrange
        category = Mock(spec=Category)
        category.name = "Test Category"
        category.user_id = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="User ID is required"):
            self.service.create(category)
        
        self.mock_repository.add.assert_not_called()
    
    def test_create_duplicate_category_name(self):
        """Test creating category with duplicate name"""
        # Arrange
        category = Mock(spec=Category)
        category.name = "Duplicate Name"
        category.user_id = 123
        
        # Mock existing category with same name
        existing_category = Mock(spec=Category)
        existing_category.id = "existing-id"
        self.mock_repository.get_by_name.return_value = existing_category
        
        # Act & Assert
        with pytest.raises(ValueError, match="Category with name 'Duplicate Name' already exists"):
            self.service.create(category)
        
        self.mock_repository.get_by_name.assert_called_once_with("Duplicate Name")
        self.mock_repository.add.assert_not_called()
    
    def test_list(self):
        """Test listing all categories"""
        # Arrange
        expected_categories = [Mock(spec=Category), Mock(spec=Category)]
        self.mock_repository.list.return_value = expected_categories
        
        # Act
        result = self.service.list()
        
        # Assert
        assert result == expected_categories
        self.mock_repository.list.assert_called_once()
    
    def test_update_valid_category(self):
        """Test updating a valid category"""
        # Arrange
        category = Mock(spec=Category)
        category.name = "Updated Category"
        category.user_id = 123
        category.id = "cat-123"
        
        # Mock repository methods for validation
        self.mock_repository.get_by_name.return_value = None  # No duplicate
        
        # Act
        self.service.update(category)
        
        # Assert
        self.mock_repository.get_by_name.assert_called_once_with("Updated Category")
        self.mock_repository.update.assert_called_once_with(category)
    
    def test_update_same_category_name_allowed(self):
        """Test updating category with same name (should be allowed)"""
        # Arrange
        category = Mock(spec=Category)
        category.name = "Same Name"
        category.user_id = 123
        category.id = "cat-123"
        
        # Mock existing category with same name and ID (same category)
        existing_category = Mock(spec=Category)
        existing_category.id = "cat-123"  # Same ID
        self.mock_repository.get_by_name.return_value = existing_category
        
        # Act
        self.service.update(category)
        
        # Assert
        self.mock_repository.get_by_name.assert_called_once_with("Same Name")
        self.mock_repository.update.assert_called_once_with(category)
    
    def test_update_duplicate_name_different_category(self):
        """Test updating category with name that exists on different category"""
        # Arrange
        category = Mock(spec=Category)
        category.name = "Duplicate Name"
        category.user_id = 123
        category.id = "cat-123"
        
        # Mock existing category with same name but different ID
        existing_category = Mock(spec=Category)
        existing_category.id = "different-id"
        self.mock_repository.get_by_name.return_value = existing_category
        
        # Act & Assert
        with pytest.raises(ValueError, match="Category with name 'Duplicate Name' already exists"):
            self.service.update(category)
        
        self.mock_repository.get_by_name.assert_called_once_with("Duplicate Name")
        self.mock_repository.update.assert_not_called()
    
    def test_delete(self):
        """Test deleting a category"""
        # Arrange
        category_id = "cat-123"
        
        # Act
        self.service.delete(category_id)
        
        # Assert
        self.mock_repository.delete.assert_called_once_with(category_id)
    
    def test_get_by_name(self):
        """Test retrieving category by name"""
        # Arrange
        name = "Test Category"
        expected_category = Mock(spec=Category)
        self.mock_repository.get_by_name.return_value = expected_category
        
        # Act
        result = self.service.get_by_name(name)
        
        # Assert
        assert result == expected_category
        self.mock_repository.get_by_name.assert_called_once_with(name)
    
    def test_get_by_name_not_found(self):
        """Test retrieving non-existent category by name"""
        # Arrange
        name = "Nonexistent Category"
        self.mock_repository.get_by_name.return_value = None
        
        # Act
        result = self.service.get_by_name(name)
        
        # Assert
        assert result is None
        self.mock_repository.get_by_name.assert_called_once_with(name)
    
    def test_validate_strips_whitespace(self):
        """Test that validation strips whitespace from category name"""
        # Arrange
        category = Mock(spec=Category)
        category.name = "  Test Category  "
        category.user_id = 123
        
        # Mock repository methods for validation
        self.mock_repository.get_by_name.return_value = None
        
        # Act
        self.service.create(category)
        
        # Assert - should call get_by_name with stripped name
        self.mock_repository.get_by_name.assert_called_once_with("Test Category")
    
    def test_validate_handles_none_name(self):
        """Test validation when category name is None"""
        # Arrange
        category = Mock(spec=Category)
        category.name = None
        category.user_id = 123
        
        # Act & Assert
        with pytest.raises(ValueError, match="Category name is required"):
            self.service.create(category)
    
    def test_validate_handles_category_without_id(self):
        """Test validation for new category without ID"""
        # Arrange
        category = Mock(spec=Category)
        category.name = "New Category"
        category.user_id = 123
        # No id attribute (new category)
        
        # Mock existing category with same name
        existing_category = Mock(spec=Category)
        existing_category.id = "existing-id"
        self.mock_repository.get_by_name.return_value = existing_category
        
        # Act & Assert
        with pytest.raises(ValueError, match="Category with name 'New Category' already exists"):
            self.service.create(category)
