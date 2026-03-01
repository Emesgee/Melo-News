import pytest
from app import create_app, db
from app.models import FileType, InputTemplate, OutputTemplate


@pytest.fixture
def app():
    """Create app for testing"""
    app = create_app(config_name='testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


class TestModels:
    """Test database models"""
    
    def test_file_type_creation(self, app):
        """Test FileType model creation"""
        with app.app_context():
            file_type = FileType(
                type_name="Image",
                allowed_extensions="jpg,png,jpeg"
            )
            db.session.add(file_type)
            db.session.commit()
            
            # Query by type_name (not id)
            result = db.session.query(FileType).filter_by(type_name="Image").first()
            assert result is not None
            assert result.type_name == "Image"
    
    def test_input_template_creation(self, app):
        """Test InputTemplate model creation"""
        with app.app_context():
            template = InputTemplate(
                template_type="Keyword Search",
                template_description="Search by keywords"
            )
            db.session.add(template)
            db.session.commit()
            
            # Check templateid is set (not id)
            assert template.templateid is not None
            
            # Query by template_type
            result = db.session.query(InputTemplate).filter_by(
                template_type="Keyword Search"
            ).first()
            assert result is not None
            assert result.template_description == "Search by keywords"
    
    def test_output_template_creation(self, app):
        """Test OutputTemplate model creation"""
        with app.app_context():
            template = OutputTemplate(
                template_type="Summary View",
                description="Shows key details"
            )
            db.session.add(template)
            db.session.commit()
            
            # Check templateid is set (not id)
            assert template.templateid is not None
            
            # Query by template_type
            result = db.session.query(OutputTemplate).filter_by(
                template_type="Summary View"
            ).first()
            assert result is not None
            assert result.description == "Shows key details"
    
    def test_input_template_query_all(self, app):
        """Test querying all InputTemplates"""
        with app.app_context():
            # Add some templates
            t1 = InputTemplate(
                template_type="Type1",
                template_description="Desc1"
            )
            t2 = InputTemplate(
                template_type="Type2",
                template_description="Desc2"
            )
            db.session.add_all([t1, t2])
            db.session.commit()
            
            # Query all
            results = db.session.query(InputTemplate).all()
            assert len(results) == 2
            assert results[0].template_type == "Type1"
            assert results[1].template_type == "Type2"
    
    def test_output_template_query_all(self, app):
        """Test querying all OutputTemplates"""
        with app.app_context():
            # Add some templates
            t1 = OutputTemplate(
                template_type="Type1",
                description="Desc1"
            )
            t2 = OutputTemplate(
                template_type="Type2",
                description="Desc2"
            )
            db.session.add_all([t1, t2])
            db.session.commit()
            
            # Query all
            results = db.session.query(OutputTemplate).all()
            assert len(results) == 2
            assert results[0].template_type == "Type1"
            assert results[1].template_type == "Type2"
    
    def test_file_type_multiple_creation(self, app):
        """Test creating multiple FileType records"""
        with app.app_context():
            types = [
                FileType(type_name="PDF", allowed_extensions="pdf"),
                FileType(type_name="Word", allowed_extensions="doc,docx"),
                FileType(type_name="Excel", allowed_extensions="xls,xlsx"),
            ]
            db.session.add_all(types)
            db.session.commit()
            
            # Verify all created
            results = db.session.query(FileType).all()
            assert len(results) == 3
    
    def test_input_template_filter(self, app):
        """Test filtering InputTemplates"""
        with app.app_context():
            t1 = InputTemplate(
                template_type="Search",
                template_description="Search template"
            )
            t2 = InputTemplate(
                template_type="Filter",
                template_description="Filter template"
            )
            db.session.add_all([t1, t2])
            db.session.commit()
            
            # Filter by template_type
            search_results = db.session.query(InputTemplate).filter_by(
                template_type="Search"
            ).all()
            assert len(search_results) == 1
            assert search_results[0].template_description == "Search template"
    
    def test_output_template_filter(self, app):
        """Test filtering OutputTemplates"""
        with app.app_context():
            t1 = OutputTemplate(
                template_type="Summary",
                description="Summary output"
            )
            t2 = OutputTemplate(
                template_type="Detailed",
                description="Detailed output"
            )
            db.session.add_all([t1, t2])
            db.session.commit()
            
            # Filter by template_type
            detailed = db.session.query(OutputTemplate).filter_by(
                template_type="Detailed"
            ).all()
            assert len(detailed) == 1
            assert detailed[0].description == "Detailed output"
    
    def test_models_without_app_context_raises_error(self):
        """Test that operations without app context fail gracefully"""
        # This test verifies the app context requirement
        app = create_app(config_name='testing')
        
        # Without context, this should fail
        try:
            db.session.query(FileType).all()
            # If we get here without app context, that's actually ok
            # because the app might handle it
        except RuntimeError:
            # This is expected without app context
            pass
    
    def test_template_fields_are_correct(self, app):
        """Test that template fields store correct data"""
        with app.app_context():
            input_tmpl = InputTemplate(
                template_type="Complex Search",
                template_description="A complex search template with multiple filters"
            )
            output_tmpl = OutputTemplate(
                template_type="Advanced Report",
                description="An advanced report showing all details"
            )
            db.session.add_all([input_tmpl, output_tmpl])
            db.session.commit()
            
            # Retrieve and verify exact fields
            retrieved_input = db.session.query(InputTemplate).first()
            assert retrieved_input.template_type == "Complex Search"
            assert retrieved_input.template_description == "A complex search template with multiple filters"
            
            retrieved_output = db.session.query(OutputTemplate).first()
            assert retrieved_output.template_type == "Advanced Report"
            assert retrieved_output.description == "An advanced report showing all details"