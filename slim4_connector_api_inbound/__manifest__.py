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


{
    'name': 'Slim4 Connector API - Inbound',
    'summary': 'Receive and stage inbound Slim4 payloads through Odoo API endpoints',
    'version': '19.0.1.0.3',
    'category': 'Technical',
    'author': 'Accomodata',
    'website': 'https://www.accomodata.be',
    'license': 'OPL-1',
    'depends': [
        'slim4_connector_api',
        'slim4_connector_base',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/slim4_inbound_message_security.xml',

        'data/slim4_inbound_cron.xml',

        'views/slim4_inbound_message_views.xml',
        'views/slim4_menuitem.xml',
    ],
    'installable': True,
    'application': False,
    'module_type': 'official',
}
