#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2009 SnelDev (http://www.sneldev.com) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import pooler
import threading

#Globals for syncrhonisation
export_lock=threading.Lock();
export_running=False;

#Thread safe version of export_running
def export_is_running():
    global export_running
    
    retVal=False
    export_lock.acquire()  
    if (export_running == False):
        export_running=True
        retVal=False
    else:
        retVal=True  
    export_lock.release()
    return retVal

def set_export_finished():
    global export_running
    export_running=False
