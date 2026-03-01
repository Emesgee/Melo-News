import pytest
from app.models import db, InputTemplate, OutputTemplate, FileType, User

class TestModels:
    """Test database models"""
    
    def test_file_type_creation(self, database):
        """Test FileType model"""
        file_type = FileType(
            type_name="Image",
            allowed_extensions="jpg, png, jpeg"
        )
        database.session.add(file_type)
        database.session.commit()
        
        assert file_type.id is not None
        assert file_type.type_name == "Image"
    
    def test_input_template_creation(self, database):
        """Test InputTemplate model"""
        template = InputTemplate(
            template_type="Keyword Search",
            template_description="Search by keywords"
        )
        database.session.add(template)
        database.session.commit()
        
        assert template.id is not None
        assert template.template_type == "Keyword Search"
    
    def test_output_template_creation(self, database):
        """Test OutputTemplate model"""
        template = OutputTemplate(
            template_type="Summary View",
            description="Shows key details"
        )
        database.session.add(template)
        database.session.commit()
        
        assert template.id is not None
        assert template.template_type == "Summary View"
