# app/templates/routes.py
from flask import Blueprint, jsonify, request
from ..models import  InputTemplate, OutputTemplate


templates_bp = Blueprint('templates', __name__)

# app/templates/routes.py
@templates_bp.route('/templates', methods=['GET'])
def get_templates():
    templates = InputTemplate.query.all()
    return jsonify([
        {
            "templateid": template.templateid,
            "template_type": template.template_type,
            "template_description": template.template_description
        }
        for template in templates
    ])

@templates_bp.route('/output_templates', methods=['GET'])
def get_output_templates():
    templates = OutputTemplate.query.all()
    return jsonify([
        {
            "templateid": template.templateid,
            "template_type": template.template_type,
            "description": template.description
        }
        for template in templates
    ])

@templates_bp.route('/generate_output', methods=['POST'])
def generate_output():
    data = request.get_json()
    search_id = data.get("search_id")
    template_id = data.get("template_id")
    filetype_id = data.get("filetype_id")

    # Placeholder response
    output_data = {
        "message": "Output generated successfully",
        "download_link": "http://example.com/download/output_file.zip"
    }
    return jsonify(output_data)

