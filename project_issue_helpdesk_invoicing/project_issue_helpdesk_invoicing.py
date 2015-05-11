# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Addons modules by CLEARCORP S.A.
#    Copyright (C) 2009-TODAY CLEARCORP S.A. (<http://clearcorp.co.cr>).
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
from openerp import models, fields, api, _
from openerp.exceptions import Warning
from datetime import date
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.addons.decimal_precision import decimal_precision as dp

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    issue_ids=fields.One2many('project.issue','sale_order_id')
    task_ids=fields.One2many('project.task','sale_id')

class ProjectIssue(models.Model):
    _inherit = 'project.issue'
    @api.v7
    def write(self, cr, uid, ids, vals, context=None):
        issues=self.browse(cr,uid,ids)
        if vals.get('stage_id'):
            type_obj=self.pool.get('project.task.type')
            type_ids=type_obj.search(cr, uid,[('id', '=', vals.get('stage_id'))])
            types=type_obj.browse(cr, uid,type_ids)
            for type in types:
                if type.closed==True:
                    for issue in issues:
                        for backorder in issue.backorder_ids:
                            if backorder.state!='done':
                                raise Warning(_('Pending transfer the backorder: %s' % backorder.name))
                            elif not backorder.delivery_note_id:
                                raise Warning(_('Pending generate delivery note for backorder: %s' % backorder.name))
                        for expense_line in issue.expense_line_ids:
                            if not expense_line.expense_id.state in ['done','pain']:
                                raise Warning(_('Pending change status to done or paid of expense: %s' % expense_line.expense_id.name))
        return super(ProjectIssue, self).write(cr, uid, ids, vals, context)
   
    expense_line_ids=fields.One2many('hr.expense.line','issue_id')
    sale_order_id=fields.Many2one('sale.order','Sale Order')
    invoice_sale_id=fields.Char(string='Invoice Number',related='sale_order_id.invoice_ids.internal_number')
    invoice_ids=fields.Many2many('account.invoice','account_invoice_project_issue_rel',string='Invoices Numbers')
    
class ResPartner(models.Model):
    _inherit = 'res.partner'
    is_provision=fields.Boolean('Provision Apply')

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    @api.v7
    def create(self,cr, uid, vals, context=None):
        if 'invoice_partner_type' in vals and vals.get('invoice_partner_type')=='branch' and (vals.get('branch_ids')==False or not 'invoice_partner_type' in vals):
            raise Warning(_('Not branches in contract'))
        return super(AccountAnalyticAccount, self).create(cr, uid, vals, context=context)
    @api.v7
    def write(self, cr, uid, ids, vals, context=None):
        if 'invoice_partner_type' in vals and vals.get('invoice_partner_type')=='branch' and not 'branch_ids' in vals:
            for contract in self.browse(cr,uid,ids,context):
                if not contract.branch_ids:
                    raise Warning(_('Not branches in contract'))
        return super(AccountAnalyticAccount, self).write(cr, uid, ids, vals, context)
    @api.depends('preventive_check_interval_number','preventive_check_interval_type')
    @api.one
    def get_interval_invoice(self):
        if self.invoice_preventive_check==True:
            self.preventive_check_interval_invoice=str(self.preventive_check_interval_number)+ ' ' + self.preventive_check_interval_type
        else:
            self.preventive_check_interval_invoice=False
    branch_ids=fields.Many2many('res.partner','account_analytic_partner_rel')
    holidays_calendar_id=fields.Many2one('holiday.calendar',string="Holidays Calendar")
    pricelist_ids=fields.One2many('contract.pricelist','contract_id')
    product_preventive_check_ids=fields.One2many('contract.preventive.check','contract_id')
    regular_schedule_id=fields.Many2one('resource.calendar',string="Regular Schedule")
    invoice_preventive_check= fields.Boolean('Preventive Check and Periodic Rate')
    amount_preventive_check= fields.Float('Mount to Invoice')
    invoice_partner_type=fields.Selection([('customer','By Customer'),('branch','By Branch')],string="Invoice type")
    preventive_check_interval_number=fields.Integer(string="Repeat Every")
    preventive_check_interval_type=fields.Selection([('days','Days'),('weeks','Weeks'),('months','Months')],string="Interval Type")
    preventive_check_interval_invoice=fields.Char("Interval Invoice",compute='get_interval_invoice')
    currency_id=fields.Many2one(related='pricelist_id.currency_id',string='Currency',store=True)
    _defaults={
            'invoice_partner_type':'customer',
            'preventive_check_interval_number':1,
            'preventive_check_interval_type':'months',
            'preventive_check_invoice_date': lambda *a: time.strftime('%Y-%m-%d'),
            }

class HRExpenseLine(models.Model):
    _inherit = 'hr.expense.line'
    @api.depends('issue_id')
    @api.one
    def get_account_issue(self):
        account_obj=self.env['account.analytic.account']
        if self.issue_id:
            self.init_onchange_call=self.issue_id.analytic_account_id
        else:
            self.init_onchange_call=account_obj.search([('type','in',['normal','contract'])])
    @api.onchange('issue_id')
    def get_account(self):
        if self.issue_id.analytic_account_id:
            self.analytic_account=self.issue_id.analytic_account_id
        else:
            self.analytic_account=False
    init_onchange_call= fields.Many2many('account.analytic.account',compute="get_account_issue",string='Nothing Display', help='field at view init')
    issue_id=fields.Many2one('project.issue','Issue')
    
        
class HolidayCalendar(models.Model):
    _name = 'holiday.calendar'
    holiday_ids=fields.One2many('holiday.calendar.date','holidays_calendar_id')
    name=fields.Char(size=256,required=True,string="Calendar Name")
    contract_ids=fields.One2many('account.analytic.account','holidays_calendar_id')
    
class HolidayCalendarDate(models.Model):
    _name = 'holiday.calendar.date'
 
    name=fields.Char(size=256,required=True,string="Holiday Name")
    date=fields.Date(required=True,string="Date")
    notes=fields.Text(string="Notes")
    holidays_calendar_id=fields.Many2one('holiday.calendar',string="Holidays Calendar")
     
class ContractPriceList(models.Model):
    _name = 'contract.pricelist'
    
    @api.onchange('pricelist_line_type')
    def onchange_pricelist_line_type(self):
        if self.pricelist_line_type:
            if self.pricelist_line_type=='category':
                self.product_id=""
            elif self.pricelist_line_type=='product':
                self.categ_id=""
        elif not self.pricelist_line_type:
             self.product_id=""
             self.categ_id=""
             
    @api.constrains('pricelist_line_type')
    def _check_lines(self):
        for line in self:
            if line.pricelist_line_type=='category':
                exist_category=self.search([('categ_id','=', line.categ_id.id),('contract_id','=', line.contract_id.id)])
                if len(exist_category)>1:
                        raise Warning('Contract only allow a line to a single category',['categ_id'])
            elif line.pricelist_line_type=='product':
                exist_product = self.search([('product_id','=', line.product_id.id),('contract_id','=', line.contract_id.id)])
                if len(exist_product)>1:
                    raise Warning('Contract only allow a line to a single product',['product_id'])
        return True
    
    @api.constrains('technical_rate','assistant_rate')
    def _check_rates(self):
        for rate in self:
            if (rate.technical_rate<1.0 or rate.assistant_rate<1.0):
                raise Warning('Rates must be greater or equal to one',['technical_rate','assistant_rate'])
        return True
    
    @api.constrains('overtime_multiplier','holiday_multiplier')
    def _check_multipliers(self):
        for multipliers in self:
            if (multipliers.overtime_multiplier<1.0 or multipliers.holiday_multiplier<1.0):
                raise Warning('Multipliers must be greater or equal to one',['overtime_multiplier','holiday_multiplier'])
        return True
    
    contract_id=fields.Many2one('account.analytic.account',string="Contract")
    pricelist_line_type=fields.Selection([('category','Category'),('product','Product')],string="Pricelist Type")
    categ_id=fields.Many2one('product.category',string="Category Product")
    product_id=fields.Many2one('product.product',string="Product")
    technical_rate=fields.Float(digits=(16,2),required=True,string="Technical Rate")
    assistant_rate=fields.Float(digits=(16,2),required=True,string="Assistant Rate")
    overtime_multiplier=fields.Float(digits=(16,2),required=True,string="Overtime Multiplier")
    holiday_multiplier=fields.Float(digits=(16,2),required=True,string="Holiday Multiplier")
    minimum_time=fields.Float(required=True,string="Minimum Time")
     
    _defaults={
        'technical_rate':0.0,
        'assistant_rate':0.0,
        'overtime_multiplier':1.0
        }
    
class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def get_profitability_line(self,invoice_line):
        invoice_line.write({'real_price':invoice_line.price_subtotal})
        for invoice_sale_line in invoice_line.sale_lines:
            invoice_line.write({'quoted_cost':invoice_sale_line.product_uom_qty*invoice_sale_line.purchase_price})
            invoice_line.write({'quoted_price':invoice_sale_line.price_subtotal})
            invoice_line.write({'real_cost':(invoice_line.quantity*invoice_sale_line.purchase_price)})
        if not invoice_line.sale_lines:
            invoice_line.write({'quoted_cost':0.0})
            invoice_line.write({'quoted_price':0.0})
            invoice_line.write({'real_cost':invoice_line.product_id.standard_price*invoice_line.quantity})
        invoice_line.write({'expected_margin':invoice_line.quoted_price-invoice_line.quoted_cost})
        invoice_line.write({'real_margin':invoice_line.real_price-invoice_line.real_cost})
        invoice_line.write({'variation_cost':invoice_line.real_cost-invoice_line.quoted_cost})
        invoice_line.write({'variation_price':invoice_line.real_price-invoice_line.quoted_price})
        invoice_line.write({'variation_margin':invoice_line.real_margin-invoice_line.expected_margin})
        if invoice_line.quoted_cost!=0:
            invoice_line.write({'porcent_variation_cost':(invoice_line.real_cost-invoice_line.quoted_cost)/invoice_line.quoted_cost*100})
        else:
            invoice_line.write({'porcent_variation_cost':0.0})
        if invoice_line.quoted_price!=0:
            invoice_line.write({'porcent_variation_price':(invoice_line.real_price-invoice_line.quoted_price)/invoice_line.quoted_price*100})
        else:
            invoice_line.write({'porcent_variation_price':0.0})
        if invoice_line.invoice_id.variation_margin!=0.0:
            invoice_line.write({'porcent_variation_margin':invoice_line.invoice_id.porcent_variation_margin*((invoice_line.real_margin-invoice_line.expected_margin)/invoice_line.invoice_id.variation_margin*100)/100})
        else:
            invoice_line.write({'porcent_variation_margin':0.0})

    @api.multi
    @api.depends('invoice_line','quoted_cost','quoted_price','real_cost','real_price')
    def get_profitability(self):
        for invoice in self:
            if invoice.order_ids and not invoice.order_ids.issue_ids:
                quoted_cost=0.0
                quoted_price=0.0
                real_cost=0.0
                real_price=0.0
                for sale_line in invoice.order_ids.order_line:
                    quoted_cost+=sale_line.product_uom_qty*sale_line.purchase_price
                    quoted_price+=sale_line.price_subtotal
                invoice.quoted_cost=quoted_cost
                invoice.quoted_price=quoted_price
                for invoice_line in invoice.invoice_line:
                    real_price+=invoice_line.price_subtotal
                    if not invoice_line.sale_lines:
                        real_cost+=invoice_line.product_id.standard_price*invoice_line.quantity
                    else:
                        real_cost+=invoice_line.sale_lines.purchase_price*invoice_line.quantity
                invoice.real_price=real_price
                invoice.real_cost=real_cost
                invoice.expected_margin=invoice.quoted_price-invoice.quoted_cost
                invoice.real_margin=invoice.real_price-invoice.real_cost
                invoice.variation_cost=invoice.real_cost-invoice.quoted_cost
                invoice.variation_price=invoice.real_price-invoice.quoted_price
                invoice.variation_margin=invoice.real_margin-invoice.expected_margin
                if invoice.quoted_cost!=0:
                    invoice.porcent_variation_cost=(invoice.real_cost-invoice.quoted_cost)/invoice.quoted_cost*100
                else:
                    invoice.porcent_variation_cost=0.0
                if invoice.quoted_price!=0:
                    invoice.porcent_variation_price=(invoice.real_price-invoice.quoted_price)/invoice.quoted_price*100
                else:
                    invoice.porcent_variation_price=0.0
                if invoice.expected_margin!=0:
                    invoice.porcent_variation_margin=(invoice.real_margin-invoice.expected_margin)/invoice.expected_margin*100
                else:
                    invoice.porcent_variation_margin=0.0
                for invoice_line in invoice.invoice_line:
                    invoice.get_profitability_line(invoice_line)
            elif invoice.order_ids and invoice.order_ids.issue_ids:
                quoted_cost=0.0
                quoted_price=0.0
                real_cost=0.0
                real_price=0.0
                for sale_line in invoice.order_ids.order_line:
                    quoted_cost+=sale_line.product_uom_qty*sale_line.purchase_price
                    quoted_price+=sale_line.price_subtotal
                invoice.quoted_cost=quoted_cost
                invoice.quoted_price=quoted_price
                total_timesheet=0.0
                total_cost_timesheet=0.0
                total_backorder=0.0
                total_backorder_cost=0.0
                for issue in invoice.order_ids.issue_ids:
                    account_obj=self.env['account.analytic.account']
                    for timesheet in issue.timesheet_ids:
                        for account_line in timesheet.line_id:
                            if not account_line.invoice_id:
                                factor = self.pool.get('hr_timesheet_invoice.factor').browse(account_line.factor_id.id)
                                qty,mount=account_obj._get_invoice_price(account_line.account_id,account_line.date,timesheet.start_time,timesheet.end_time,issue.product_id.id,issue.categ_id.id,account_line.unit_amount,timesheet.service_type,timesheet.employee_id.id)
                                if account_line.account_id.pricelist_id.currency_id.id != invoice.currency_id.id:
                                    import_currency_rate=account_line.account_id.pricelist_id.currency_id.get_exchange_rate(invoice.currency_id,date.strftime(date.today(), "%Y-%m-%d"))[0]
                                else:
                                    import_currency_rate = 1
                                total_timesheet+=qty*mount*import_currency_rate*(100-factor.factor or 0.0) / 100.0
                        if timesheet.employee_id.product_id:
                            total_cost_timesheet+=(timesheet.end_time-timesheet.start_time)*timesheet.employee_id.product_id.standard_price
                    for backorder in issue.backorder_ids:
                        if backorder.delivery_note_id and backorder.invoice_state!='invoiced':
                            for delivery_note_lines in backorder.delivery_note_id.note_lines:
                                total_backorder+=delivery_note_lines.quantity*delivery_note_lines.price_unit
                        if backorder.move_lines:
                            for move in backorder.move_lines:
                                standart_price=0.0
                                quantity=0.0
                                final_cost_quant=0.0
                                if move.quant_ids:
                                    for quant in move.quant_ids:
                                        quantity+=abs(quant.qty)
                                        final_cost_quant+=(quant.cost)*abs(quant.qty)
                                    standart_price=(final_cost_quant/quantity)
                                    total_backorder_cost+=standart_price*move.product_qty
                invoice.real_price=total_timesheet+total_backorder
                invoice.real_cost=total_cost_timesheet+total_backorder_cost
                invoice.expected_margin=invoice.quoted_price-invoice.quoted_cost
                invoice.real_margin=invoice.real_price-invoice.real_cost
                invoice.variation_cost=invoice.real_cost-invoice.quoted_cost
                invoice.variation_price=invoice.real_price-invoice.quoted_price
                invoice.variation_margin=invoice.real_margin-invoice.expected_margin
                if invoice.quoted_cost!=0:
                    invoice.porcent_variation_cost=(invoice.real_cost-invoice.quoted_cost)/invoice.quoted_cost*100
                else:
                    invoice.porcent_variation_cost=0.0
                if invoice.quoted_price!=0:
                    invoice.porcent_variation_price=(invoice.real_price-invoice.quoted_price)/invoice.quoted_price*100
                else:
                    invoice.porcent_variation_price=0.0
                if invoice.expected_margin!=0:
                    invoice.porcent_variation_margin=(invoice.real_margin-invoice.expected_margin)/invoice.expected_margin*100
                else:
                    invoice.porcent_variation_margin=0.0
        
    @api.multi
    def unlink(self):
        for invoice in self:
            for issue in invoice.issue_ids:
                if issue:
                    for backorder in issue.backorder_ids:
                        if backorder.invoice_state=='invoiced':
                            backorder.write({'invoice_state':'none'})
                            backorder.move_lines.write({'invoice_state':'none'})
            for task in invoice.task_ids:
                for backorder in task.backorder_ids:
                        if backorder.invoice_state=='invoiced':
                            backorder.write({'invoice_state':'none'})
                            backorder.move_lines.write({'invoice_state':'none'})
        return models.Model.unlink(self)
    task_ids=fields.One2many('project.task','invoice_id')
    issue_ids=fields.Many2many('project.issue','account_invoice_project_issue_rel',string='Issues')
    quoted_cost=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Quoted Cost")
    quoted_price=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Quoted Price")
    expected_margin=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Expected Margin")
    real_cost=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Real Cost")
    real_price=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Real Price")
    real_margin=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Real Margin")
    variation_cost=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Variation Cost")
    variation_price=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Variation Price")
    variation_margin=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Variation Margin")
    porcent_variation_cost=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Variation Cost %")
    porcent_variation_price=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Variation Price %")
    porcent_variation_margin=fields.Float(compute="get_profitability",store=True, readonly=True,digits=(16,2),string="Variation Margin %")
    order_ids= fields.Many2many('sale.order', 'sale_order_invoice_rel', 'invoice_id','order_id', 'Sales Order', readonly=True, copy=False, help="This is the list of sales orders that have been generated for this invoice.")

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    quoted_cost=fields.Float(digits=(16,2),string="Quoted Cost")
    quoted_price=fields.Float(digits=(16,2),string="Quoted Price")
    expected_margin=fields.Float(digits=(16,2),string="Expected Margin")
    real_cost=fields.Float(digits=(16,2),string="Real Cost")
    real_price=fields.Float(digits=(16,2),string="Real Price")
    real_margin=fields.Float(digits=(16,2),string="Real Margin")
    variation_cost=fields.Float(digits=(16,2),string="Variation Cost")
    variation_price=fields.Float(digits=(16,2),string="Variation Price")
    variation_margin=fields.Float(digits=(16,2),string="Variation Margin")
    porcent_variation_cost=fields.Float(digits=(16,2),string="Variation Cost(%)")
    porcent_variation_price=fields.Float(digits=(16,2),string="Variation Price(%)")
    porcent_variation_margin=fields.Float(digits=(16,2),string="Variation Margin(%)")
    sale_lines= fields.Many2many('sale.order.line', 'sale_order_line_invoice_rel', 'invoice_id','order_line_id', 'Sale Lines', readonly=True, copy=False)

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    @api.constrains('warranty_manufacturer')
    def check_note_lines(self):
        journal_obj=self.env['account.journal']
        journal_id=journal_obj.search([('warranty_manufacturer', '!=', False),('id', '!=', self.id)])
        if journal_id and self.warranty_manufacturer==True:
            raise Warning(_('Already exist a journal asiggned for warranty manufacturer.  (%s)' %(journal_id.name)))
    warranty_manufacturer=fields.Boolean('Apply to warranty manufacturer')

class ProjectTask(models.Model):
    _inherit = 'project.task'
    @api.v7
    def create(self, cr, uid, vals, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if 'name' in vals:
            if len(vals.get('name'))>user.company_id.maximum_name_task:
                raise Warning(_('The task name exceeds the limit of %i characters.' %user.company_id.maximum_name_task))
        result = super(ProjectTask, self).create(cr, uid, vals, context=context)
        return result
    @api.v7
    def write(self, cr, uid, ids, vals, context=None):
        tasks=self.browse(cr,uid,ids,context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if vals.get('stage_id'):
            type_obj=self.pool.get('project.task.type')
            type_ids=type_obj.search(cr, uid,[('id', '=', vals.get('stage_id'))])
            types=type_obj.browse(cr, uid,type_ids)
            for type in types:
                if type.closed==True:
                    for task in tasks:
                        for backorder in task.backorder_ids:
                            if backorder.state!='done':
                                raise Warning(_('Pending transfer the backorder: %s' % backorder.name))
                            elif not backorder.delivery_note_id:
                                raise Warning(_('Pending generate delivery note for backorder: %s' % backorder.name))
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if 'name' in vals:
            if len(vals.get('name'))>user.company_id.maximum_name_task:
                raise Warning(_('The task name exceeds the limit of %i characters.' %user.company_id.maximum_name_task))
        res = super(ProjectTask, self).write(cr, uid, ids, vals, context=context)
        return res
    extra=fields.Boolean(string="Is extra")
    sale_id=fields.Many2one('sale.order',string="Sale Order")
    invoice_id=fields.Many2one('account.invoice',string='Invoice Number')
    
class ContractPreventiveCheck(models.Model):
    _name = 'contract.preventive.check'

    def get_next_execute_issue(self,line):
        date_execute_issue=False
        if line.date_execute_issue:
            if line.interval_type=='days':
                date_execute_issue= datetime.strptime(line.date_execute_issue, '%Y-%m-%d %H:%M:%S') + relativedelta(days=+line.interval_number)
            elif line.interval_type=='weeks':
                date_execute_issue=datetime.strptime(line.date_execute_issue, '%Y-%m-%d %H:%M:%S') + relativedelta(weeks=+line.interval_number)
            elif line.interval_type=='months':
                date_execute_issue=datetime.strptime(line.date_execute_issue, '%Y-%m-%d %H:%M:%S') + relativedelta(months=+line.interval_number)
        else:
            date_execute_issue=False
        return date_execute_issue
    
    @api.constrains('interval_number')
    def _check_interval(self):
        for rate in self:
            if (rate.interval_number<1.0):
                raise Warning(_('Interval number must be greater or equal to one'))
        return True
    @api.constrains('product_id')
    def _check_lines(self):
        for line in self:
            exist_product = self.search([('product_id','=', line.product_id.id),('contract_id','=', line.contract_id.id)])
            if len(exist_product)>1:
                raise Warning(_('Contract only allow a product per line'))
        return True
    @api.constrains('date_execute_issue')
    def _check_date_execute(self):
        for line in self:
            if (datetime.strptime(line.date_execute_issue, '%Y-%m-%d %H:%M:%S')<=datetime.now()):
                raise Warning(_('The date execute must be greater than the actual date'))
        return True

    def create_issues(self,cr,uid, lines,context=None):
        issue_obj=self.pool.get('project.issue')
        for line in lines:
            if not line.contract_id.date or (datetime.strptime(line.contract_id.date, '%Y-%m-%d')>=datetime.now() and line.contract_id.state not in ['close','cancelled']) :
                if line.contract_id.branch_ids and line.contract_id.partner_id:
                    for branch in line.contract_id.branch_ids:
                        create_issue={}
                        create_issue['partner_id']=line.contract_id.partner_id.id
                        create_issue['branch_id']=branch.id
                        create_issue['name']=_('Preventive Check-'+ line.product_id.name)
                        create_issue['name']=_('Preventive Check-'+ line.product_id.name)
                        create_issue['contact']=_('Generated for contract')
                        create_issue['categ_id']=line.product_id.categ_id.id
                        create_issue['product_id']=line.product_id.id
                        create_issue['issue_type']='preventive check'
                        create_issue['analytic_account_id']=line.contract_id.id
                        issue=issue_obj.create(cr,uid,create_issue,context=context)
                        line.write({'date_execute_issue':self.get_next_execute_issue(line),'first_execute_issue':True})
                elif not line.contract_id.branch_ids and line.contract_id.partner_id:
                    for partner in line.contract_id.partner_id:
                        create_issue={}
                        create_issue['partner_id']=line.contract_id.partner_id.id
                        create_issue['name']=_('Preventive Check-'+ line.product_id.name)
                        create_issue['contact']=_('Generated for contract')
                        create_issue['categ_id']=line.product_id.categ_id.id
                        create_issue['product_id']=line.product_id.id
                        create_issue['issue_type']='preventive check'
                        create_issue['analytic_account_id']=line.contract_id.id
                        issue=issue_obj.create(cr,uid,create_issue,context=context)
                        line.write({'date_execute_issue':self.get_next_execute_issue(line),'first_execute_issue':True})
    
    contract_id=fields.Many2one('account.analytic.account',string="Contract")
    product_id=fields.Many2one('product.product',string="Product")
    interval_number=fields.Integer(string="Interval Number")
    interval_type=fields.Selection([('days','Days'),('weeks','Weeks'),('months','Months')],string="Interval Type")
    date_execute_issue=fields.Datetime("Date execute issue")
    first_execute_issue=fields.Boolean("First Execute Issue")
   
    _defaults={
        'interval_number':1,
        'first_execute_issue':False
               }
class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"
    real_quantity = fields.Float(string='Real Quantity',digits=dp.get_precision('Product Unit of Measure'))
    supply_type = fields.Selection(string='Use',related='product_id.supply_type')
    reference = fields.Char(string='Reference',help="Reference of origin of line invoice")
    