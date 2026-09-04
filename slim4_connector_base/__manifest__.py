# Unless otherwise stated, Odoo Apps by ACCOMODATA BVBA
# (including the website themes)
# are published under the Odoo Proprietary License v1.0, defined as follows
#
# Odoo Proprietary License v1.0
#
# This software and associated files (the "Software") may only be used
# (executed, modified, executed after modifications) if you have purchased
# a valid license from the authors,
# or if you have received a written agreement from the authors of the Software.
# You may develop Odoo modules that use the Software as a library
# (typically by depending on it, importing it and using its resources),
# but without copying any source code or material from the Software.
# You may distribute those modules under the license of your choice,
# provided that this license is compatible with the terms of the
# Odoo Proprietary License.
# It is forbidden to publish, distribute, sublicense, or sell copies of
# the Software or modified copies of the Software.
# The above copyright notice and this permission notice must be included
# in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
#
{
    'name': 'Slim4 Connector Base',
    'summary': 'Configure Slim4 interfaces and Odoo field mappings',
    'version': '19.0.1.0.1',
    'category': 'Inventory/Configuration',
    'author': 'Accomodata',
    'website': 'https://www.accomodata.be',
    'license': 'OPL-1',
    'depends': [
        'base',
        'product',
        'stock',
        'purchase',
        'sale_management',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        'data/slim4_interface_data.xml',
        'data/slim4_interface_mapping_data.xml',

        'views/slim4_interface_views.xml',
        'views/slim4_interface_mapping_views.xml',
        'views/product_supplierinfo_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/slim4_menuitem.xml',

        'wizards/slim4_specific_rule_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'slim4_connector_base/static/src/fields/slim4_field_selector.xml',
        ],
    },
    'pre_init_hook': 'pre_init_hook',
    'installable': True,
    'application': False,
    'module_type': 'official',
}
