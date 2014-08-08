# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _
from operator import itemgetter

import _common as comm
import logging
_logger = logging.getLogger(__name__)

class stock_picking(osv.osv):
    _inherit = "stock.picking"

    _tipo_de_move = [
            ('raw', 'Raw'),
            ('insu', 'Input'),
            ('bac', 'Bacha'),
    ]

    def _get_tipo_de_move(self, cr, uid, context=None):
        return sorted(self._tipo_de_move, key=itemgetter(1))

    _columns = {
        'move_prod_type': fields.selection(_get_tipo_de_move, string='Product Type picking', select=True),
    }

stock_picking()
class stock_picking_in(osv.osv):
    _inherit = "stock.picking.in"

    _tipo_de_move = [
            ('raw', 'Raw'),
            ('insu', 'Input'),
            ('bac', 'Bacha'),
    ]

    def _get_tipo_de_move(self, cr, uid, context=None):
        return sorted(self._tipo_de_move, key=itemgetter(1))

    _columns = {
        'move_prod_type': fields.selection(_get_tipo_de_move, string='Product Type picking', select=True),
    }

stock_picking_in()

class stock_move(osv.osv):
    _inherit = "stock.move"

    def _get_sign(self, obj=None):
        if not obj:
            return 0

        inp = (not obj.picking_id and obj.location_id.usage in ['customer','supplier']) or \
              (obj.picking_id and obj.picking_id.type == 'in')
        if inp:
            return 1

        out = (not obj.picking_id and obj.location_dest_id.usage in ['customer','supplier']) or \
              (obj.picking_id and obj.picking_id.type == 'out')
        if out:
            return -1

        return 0


    def _get_sign_qty(self, cr, uid, ids, field_name, arg, context=None):
        # _logger.info(">> _get_field_with_sign >> 0 >> ids = %s", ids)
        # _logger.info(">> _get_field_with_sign >> 1 >> field_name = %s", field_name)
        # _logger.info(">> _get_field_with_sign >> 2 >> arg = %s", arg)
        # _logger.info(">> _get_field_with_sign >> 3 >> context = %s", context)

        if not ids:
            return {}

        res = {}
        bal = 0.00

        ids_by_date = self.search(cr, uid, [('id','in',ids)], order='date')
        for m in self.browse(cr, uid, ids_by_date):

            fields = {}
            sign = self._get_sign(m)

            fields['qty_dimension'] = sign * m.dimension_qty
            fields['qty_product'] = sign * m.product_qty

            _logger.info(">> _get_field_with_sign >> 88 >> bal = %s", bal)
            bal += fields['qty_product']
            _logger.info(">> _get_field_with_sign >> 99 >> bal = %s", bal)

            fields['qty_balance'] = bal

            res[m.id] = fields

        _logger.info(">> _get_field_with_sign >> 5 >> res = %s", res)
        return res


    def _is_raw(self, cr, uid, ids, field_name, arg, context=None):
        """
        Determina si [ids stock_move] tiene  producto, del tipo is_raw si/no...
        """
        res = {}
        if not ids:
            return res

        # para cada stock_move -> recupero su correspondiente prod_id
        prod_ids = [sm.product_id.id for sm in self.browse(cr, uid, ids)]

        # recupero is_raw por cada producto: {prod_id: is_raw}
        data = comm.is_raw_material_by_product_id(self, cr, uid, prod_ids)

        # convierto de {prod_id: is_raw} -> {stock_move_id: is_raw}:
        res = {ids[k]: (data[prod_ids[k]] or False) for k in range(len(ids))}

        # _logger.info("10 >> _is_raw >> res = %s", res)
        return res

    def _get_move_name(self, cr, uid, pro_id=False, dim_id=False):
        name = ''
        if not pro_id:
            return name

        obj_pro = self.pool.get('product.product')
        name = obj_pro.name_get(cr, uid, [pro_id], context=None)[0][1]

        if not dim_id or \
           not comm.is_raw_material_by_product_id(self, cr, uid, [pro_id])[pro_id]:
            return name

        obj_dim = self.pool.get('product.marble.dimension')
        d = obj_dim.browse(cr, uid, [dim_id])[0]

        name = "%s >> %s" % (name, d.dimension)
        return name

    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):
        """
        Sobrecargo funcion,
        Agrego estado de Marble referente al Producto.
        """
        v = {}
        res = super(stock_move, self).onchange_product_id(cr, uid, ids, prod_id, loc_id, loc_dest_id, partner_id)
        if (not res) or (not prod_id):
            return v

        v['name'] = self._get_move_name(cr, uid, pro_id=prod_id, dim_id=False)
        v['is_raw'] = comm.is_raw_material_by_product_id(self, cr, uid, [prod_id])[prod_id]
        if not v['is_raw']:
            v.update({'dimension_id': False})
            v.update({'dimension_qty': 0})
            v.update({'product_qty': 0})

        res['value'].update(v)
        # _logger.info("12 >> onchange_product_id >> res = %s", res)
        return res

    def onchange_dimension_id(self, cr, uid, ids, pro_id=False, dim_id=False, dim_qty=False):
        v = {}
        v['name'] = self._get_move_name(cr, uid, pro_id, dim_id)
        _logger.info("1 >> onchange_dimension_id >> v = %s", v)

        res = self.onchange_dimension_qty(cr, uid, ids, dim_id, dim_qty)
        _logger.info("2 >> onchange_diemnsion_id >> res = %s", res)

        if res and res['value']:
            res['value'].update(v)
        elif v:
            res['value'] = v

        _logger.info("3 >> onchange_diemnsion_id >> res = %s", res)
        return res

    def onchange_dimension_qty(self, cr, uid, ids, dimension_id=False, dimension_qty=False):
        """
        Calcula "product qty", m2 segun cantidad de plaas ingresadas.
        """
        v = {}
        if not dimension_id:
            return v

        # defino m2
        obj = self.pool.get('product.marble.dimension')
        data = obj.read(cr, uid, [dimension_id], ['m2'], context=None)

        m2 = 0.00
        if len(data) > 0 and len(data[0]) > 0:
            m2 = data[0]['m2']

        m2 = m2 * dimension_qty
        v.update({'product_qty': m2})

        _logger.info("204 >> onchange_dimension_qty >> v = %s", v)
        return {'value': v}

    def _check_data_before_save(self, cr, uid, data, is_new=False):
        """
        Si el Producto es del tipo Marble >> debo incorporar/validar:
            - product_uom
            - product_qty
        Estos datos no son incorporados en 'data' por ser
        campos de solo lectura en la vista.
        """
        _logger.info(">> _check_data_before_save >> 50 >> data = %s", data)

        # pro = 'product_id'  in data
        # uom = 'product_uom' in data
        # qty = 'product_qty' in data

        # process = is_new or (pro and uom and qty)
        # if not process:
        #     return None

        pid = 'product_id'  in data
        did = 'dimension_id' in data
        qty = 'dimension_qty' in data

        if not (pid or did or qty):
            return

        # get stock-move (TODO interpreto un unico id)
        # obj = self.pool.get('stock.move')
        # mov = obj.browse(cr, uid, ids, context=None)[0]

        pid = data.get('product_id', False)
        if not pid:
            return

        is_raw = comm.is_raw_material_by_product_id(self, cr, uid, [pid])[pid]
        if not is_raw:
            return

        # set uom...
        # uom_m2 = comm.get_uom_m2_id(self, cr, uid)
        # prod_uom = data.get('product_uom', -1)
        # if prod_uom != uom_m2:
        #     prod_uom = uom_m2
        #     if is_new:
        #         data.update({'product_uom': uom_m2})

        # prod_qty = data.get('product_qty', False)

        # set qty...
        dim_id = data.get('dimension_id', False)
        dim_qty = data.get('dimension_qty', False)
        if dim_id:
        # qty = self.onchange_dimension_qty(cr, uid, [], dimension_id, dimension_qty)
            dim = self.onchange_dimension_id(cr, uid, [], pid, dim_id, dim_qty)
            # _logger.info(">> _check_data_before_save >> 51 >> dim = %s", dim)

            data.update({'name': dim['value']['name']})
            data.update({'product_qty': dim['value']['product_qty']})

        # _logger.info(">> _check_data_before_save >> 52 >> data = %s", data)
        return

    def create(self, cr, uid, data, context=None):
        # _logger.info(">> create >> antes >> 20 >> data = %s", data)
        self._check_data_before_save(cr, uid, data, True)

        # _logger.info(">> create >> despues >> 30 >> data = %s", data)
        return super(stock_move, self).create(cr, uid, data, context=context)


    def write(self, cr, uid, ids, vals, context=None):
        # x = self.pool.get('stock.picking.in')._search(cr, uid, 'assigned', 'raw')
        # _logger.info(">> test_search >> xxx = %s", x)

        # _logger.info(">> write >> antes >> 1 >> ids = %s", ids)
        # _logger.info(">> write >> antes >> 2 >> vals = %s", vals)
        self._check_data_before_save(cr, uid, vals, False)

        # _logger.info(">> write >> despues >> 3 >> vals = %s", vals)
        return super(stock_move, self).write(cr, uid, ids, vals, context=context)

    _columns = {
        'dimension_id': fields.many2one('product.marble.dimension', 'Dimension', select=True, states={'done': [('readonly', True)]}, domain=[('state','=','done')]),
        'dimension_qty': fields.integer('Quantity', size=3, states={'done': [('readonly', True)]}),
        'is_raw': fields.function(_is_raw, type='boolean', string='Is Marble'),

        'employee': fields.many2one('hr.employee', 'Empleado', select=True, states={'done': [('readonly', True)]}, domain=[('active','=',True)]),

        'partner_picking_id': fields.related('picking_id', 'partner_id', type='many2one', relation='res.partner', string='Patern', store=False),

        'qty_dimension': fields.function(_get_sign_qty, string='Dimension Qty', multi="sign"),
        'qty_product': fields.function(_get_sign_qty, string='Product Qty', multi="sign"),
        'qty_balance': fields.function(_get_sign_qty, string='Balance Qty', multi="sign"),
    }


    _defaults = {
        'dimension_id': False,
        'dimension_qty': 0,
    }

stock_move()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
