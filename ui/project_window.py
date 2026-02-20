import ttkbootstrap as tb
from ttkbootstrap.constants import RIGHT, LEFT
from tkinter import Toplevel, messagebox, simpledialog, Listbox, Scrollbar
from utils.validators import validate_amount, validate_date


class AutocompleteDialog:
    """Dialog with autocomplete dropdown for selecting from existing items or creating new ones"""
    def __init__(self, parent, title, prompt, suggestions, auto_select=False, is_job=False):
        """
        parent: parent window
        title: dialog title
        prompt: label text
        suggestions: list of existing names/items
        auto_select: if True, selecting from dropdown auto-confirms
        is_job: if True, job field is required
        """
        self.result_name = None
        self.result_job = None
        self.auto_select = auto_select
        self.is_job = is_job
        self.suggestions = suggestions
        self.parent = parent
        
        self.dialog = Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.geometry('400x250')
        self.dialog.resizable(False, False)
        
        from tkinter import Frame, Button
        
        # Main frame
        main_frame = Frame(self.dialog, bg='#2b2b2b')
        main_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Label
        label = tb.Label(main_frame, text=prompt, font=('Segoe UI', 9))
        label.pack(pady=5, padx=15)
        
        # Entry field
        self.entry = tb.Entry(main_frame, font=('Segoe UI', 9), width=35)
        self.entry.pack(pady=3, padx=15, fill='x')
        self.entry.bind('<KeyRelease>', self.on_entry_change)
        self.entry.bind('<Return>', self.on_ok)
        self.entry.bind('<Down>', self.on_dropdown_toggle)
        
        # Listbox for suggestions
        listbox_frame = Frame(main_frame, bg='#2b2b2b')
        listbox_frame.pack(pady=3, padx=15, fill='both', expand=True)
        
        scrollbar = Scrollbar(listbox_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.listbox = Listbox(listbox_frame, font=('Segoe UI', 9), 
                              yscrollcommand=scrollbar.set, height=6)
        scrollbar.config(command=self.listbox.yview)
        self.listbox.pack(side='left', fill='both', expand=True)
        self.listbox.bind('<Return>', self.on_listbox_select)
        self.listbox.bind('<Button-1>', self.on_listbox_select)
        
        # Update listbox on startup
        self.update_listbox()
        
        # Buttons frame
        btn_frame = Frame(main_frame, bg='#2b2b2b')
        btn_frame.pack(pady=8, fill='x', expand=True)
        
        ok_btn = Button(btn_frame, text='موافق', command=self.on_ok, 
                       bg='#28a745', fg='white', font=('Segoe UI', 9), 
                       relief='raised', bd=1, height=4)
        ok_btn.pack(side='left', fill='both', expand=True, padx=2)
        
        cancel_btn = Button(btn_frame, text='إلغاء', command=self.on_cancel, 
                          bg='#dc3545', fg='white', font=('Segoe UI', 9), 
                          relief='raised', bd=1, height=4)
        cancel_btn.pack(side='left', fill='both', expand=True, padx=2)
        
        # Bind escape
        self.dialog.bind('<Escape>', lambda e: self.on_cancel())
        
        # Handle window close button (X)
        self.dialog.protocol('WM_DELETE_WINDOW', self.on_cancel)
        
        # Focus entry
        self.dialog.after(100, lambda: self.entry.focus_set())
        
        self.dialog.wait_window()
    
    def update_listbox(self):
        """Update listbox with matching suggestions"""
        self.listbox.delete(0, 'end')
        query = self.entry.get().strip().lower()
        
        if not query:
            # Show all suggestions if entry is empty
            for item in self.suggestions:
                self.listbox.insert('end', item)
        else:
            # Show matching suggestions
            for item in self.suggestions:
                if query in item.lower():
                    self.listbox.insert('end', item)
    
    def on_entry_change(self, event=None):
        """Update listbox as user types"""
        self.update_listbox()
    
    def on_dropdown_toggle(self, event=None):
        """Switch focus to listbox on down arrow"""
        if self.listbox.size() > 0:
            self.listbox.focus_set()
            self.listbox.selection_set(0)
    
    def on_listbox_select(self, event=None):
        """Handle listbox selection"""
        selection = self.listbox.curselection()
        if selection:
            selected = self.listbox.get(selection[0])
            self.entry.delete(0, 'end')
            self.entry.insert(0, selected)
            self.listbox.delete(0, 'end')
            
            # If auto_select is enabled, automatically confirm on selection
            if self.auto_select:
                self.dialog.after(100, self.on_ok)
    
    def on_ok(self, event=None):
        """Confirm selection"""
        name = self.entry.get().strip()
        if not name:
            messagebox.showwarning('تنبيه', 'الرجاء إدخال اسم أو اختيار من القائمة', parent=self.dialog)
            return
        
        # If this is a job field, make it required
        if self.is_job and not name:
            messagebox.showwarning('تنبيه', 'الرجاء إدخال المهنة أو اختيارها من القائمة', parent=self.dialog)
            return
        
        self.result_name = name
        self.dialog.destroy()
    
    def on_cancel(self, event=None):
        """Cancel dialog"""
        self.result_name = None
        self.result_job = None
        self.dialog.destroy()


class ProjectWindow:
    def __init__(self, db, project_id, on_update_callback=None, project_name=None):
        self.db = db
        self.project_id = project_id
        self.on_update_callback = on_update_callback
        self.win = Toplevel()
        if project_name:
            self.win.title(f'تفاصيل المشروع: {project_name}')
        else:
            self.win.title('تفاصيل المشروع')
        self.win.geometry('820x560')
        self.selected_worker = None
        self.selected_importer = None
        self._build_ui()
        self.load_all()

    def ask_string_focused(self, title, prompt, initialvalue=''):
        """Ask for string with auto-focused entry field"""
        from tkinter import Button, Frame
        dialog = Toplevel(self.win)
        dialog.title(title)
        dialog.transient(self.win)
        dialog.grab_set()
        dialog.geometry('380x120')
        dialog.resizable(False, False)
        
        # Main frame
        main_frame = Frame(dialog, bg='#2b2b2b')
        main_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Label
        label = tb.Label(main_frame, text=prompt, font=('Segoe UI', 9))
        label.pack(pady=5, padx=15)
        
        # Entry with auto-focus
        entry = tb.Entry(main_frame, font=('Segoe UI', 9), width=35)
        entry.pack(pady=3, padx=15, fill='x')
        entry.insert(0, initialvalue)
        if initialvalue:
            entry.select_range(0, len(initialvalue))
        
        result = [None]
        
        def ok(event=None):
            result[0] = entry.get()
            dialog.destroy()
        
        def cancel(event=None):
            result[0] = None
            dialog.destroy()
        
        # Buttons frame - fills width
        btn_frame = Frame(main_frame, bg='#2b2b2b')
        btn_frame.pack(pady=8, fill='x', expand=True)
        
        # Buttons fill half width each
        ok_btn = Button(btn_frame, text='موافق', command=ok, bg='#28a745', fg='white', font=('Segoe UI', 9), relief='raised', bd=1, height=4)
        ok_btn.pack(side='left', fill='both', expand=True, padx=2)
        
        cancel_btn = Button(btn_frame, text='إلغاء', command=cancel, bg='#dc3545', fg='white', font=('Segoe UI', 9), relief='raised', bd=1, height=4)
        cancel_btn.pack(side='left', fill='both', expand=True, padx=2)
        
        # Bind keys
        entry.bind("<Return>", ok)
        entry.bind("<Escape>", cancel)
        dialog.bind("<Escape>", cancel)
        
        # Force focus after a brief moment to ensure it's set
        dialog.after(100, lambda: entry.focus_set())
        
        dialog.wait_window()
        return result[0]

    def _build_ui(self):
        nb = tb.Notebook(self.win)
        nb.pack(fill='both', expand=True, padx=8, pady=8)

        # Workers tab
        self.workers_frame = tb.Frame(nb)
        nb.add(self.workers_frame, text='العمال')

        w_top = tb.Frame(self.workers_frame)
        w_top.pack(fill='x')
        add_w = tb.Button(w_top, text='إضافة عامل', bootstyle='success', command=self.add_worker)
        add_w.pack(side=LEFT, padx=6, pady=6)

        self.workers_tree = tb.Treeview(self.workers_frame, columns=('job','name'), show='headings', height=8)
        self.workers_tree.heading('job', text='المهنة', anchor='e')
        self.workers_tree.heading('name', text='الاسم', anchor='e')
        self.workers_tree.column('job', anchor='e', width=160)
        self.workers_tree.column('name', anchor='e')
        self.workers_tree.pack(fill='both', expand=False, padx=6, pady=6)
        self.workers_tree.bind('<Button-3>', self.on_worker_right)
        self.workers_tree.bind('<<TreeviewSelect>>', self.on_worker_select)

        # Assignments for selected worker
        self.assign_tree = tb.Treeview(self.workers_frame, columns=('description', 'amount', 'date'), show='headings', height=6)
        self.assign_tree.heading('description', text='وصف العمل', anchor='e')
        self.assign_tree.heading('amount', text='المبلغ', anchor='e')
        self.assign_tree.heading('date', text='التاريخ', anchor='e')
        self.assign_tree.column('description', anchor='e', width=150)
        self.assign_tree.column('amount', anchor='e', width=80)
        self.assign_tree.column('date', anchor='e', width=80)
        self.assign_tree.tag_configure('paid', foreground='green')
        self.assign_tree.pack(fill='both', expand=True, padx=6, pady=6)
        self.assign_tree.bind('<Button-3>', self.on_assignment_right)

        ops_frame = tb.Frame(self.workers_frame)
        ops_frame.pack(fill='x', pady=6)
        add_assign_btn = tb.Button(ops_frame, text='+ إضافة مبلغ مخصص', bootstyle='primary', command=self.add_assignment_for_worker)
        add_assign_btn.pack(side=LEFT, padx=6)
        add_pay_btn = tb.Button(ops_frame, text='+ دفعة مدفوعه', bootstyle='success', command=self.add_payment_for_selected_worker_assignment)
        add_pay_btn.pack(side=LEFT, padx=6)

        # Importers tab (موردون)
        self.imp_frame = tb.Frame(nb)
        nb.add(self.imp_frame, text='الموردون')

        imp_top = tb.Frame(self.imp_frame)
        imp_top.pack(fill='x')
        add_i = tb.Button(imp_top, text='إضافة مورد', bootstyle='success', command=self.add_importer)
        add_i.pack(side=LEFT, padx=6, pady=6)

        self.imp_tree = tb.Treeview(self.imp_frame, columns=('job','name'), show='headings', height=8)
        self.imp_tree.heading('job', text='السلعة/الوظيفة', anchor='e')
        self.imp_tree.heading('name', text='الاسم', anchor='e')
        self.imp_tree.column('job', anchor='e', width=160)
        self.imp_tree.column('name', anchor='e')
        self.imp_tree.pack(fill='both', expand=False, padx=6, pady=6)
        self.imp_tree.bind('<Button-3>', self.on_importer_right)
        self.imp_tree.bind('<<TreeviewSelect>>', self.on_importer_select)

        self.imp_assign_tree = tb.Treeview(self.imp_frame, columns=('description', 'amount', 'date'), show='headings', height=6)
        self.imp_assign_tree.heading('description', text='وصف العمل', anchor='e')
        self.imp_assign_tree.heading('amount', text='المبلغ', anchor='e')
        self.imp_assign_tree.heading('date', text='التاريخ', anchor='e')
        self.imp_assign_tree.column('description', anchor='e', width=150)
        self.imp_assign_tree.column('amount', anchor='e', width=80)
        self.imp_assign_tree.column('date', anchor='e', width=80)
        self.imp_assign_tree.tag_configure('paid', foreground='green')
        self.imp_assign_tree.pack(fill='both', expand=True, padx=6, pady=6)
        self.imp_assign_tree.bind('<Button-3>', self.on_assignment_right)

        ops_imp = tb.Frame(self.imp_frame)
        ops_imp.pack(fill='x', pady=6)
        add_imp_assign = tb.Button(ops_imp, text='+ إضافة مبلغ مخصص', bootstyle='primary', command=self.add_assignment_for_importer)
        add_imp_assign.pack(side=LEFT, padx=6)
        add_imp_pay = tb.Button(ops_imp, text='+ دفعة مدفوعه', bootstyle='success', command=self.add_payment_for_selected_importer_assignment)
        add_imp_pay.pack(side=LEFT, padx=6)

        # Customer tab
        self.cust_frame = tb.Frame(nb)
        nb.add(self.cust_frame, text='العميل')

        self.cust_summary = tb.Label(self.cust_frame, text='', anchor='e')
        self.cust_summary.pack(fill='x', padx=6, pady=6)

        self.cust_assign_tree = tb.Treeview(self.cust_frame, columns=('description', 'amount', 'date'), show='headings', height=8)
        self.cust_assign_tree.heading('description', text='وصف العمل', anchor='e')
        self.cust_assign_tree.heading('amount', text='المبلغ', anchor='e')
        self.cust_assign_tree.heading('date', text='التاريخ', anchor='e')
        self.cust_assign_tree.column('description', width=150, anchor='e')
        self.cust_assign_tree.column('amount', width=80, anchor='e')
        self.cust_assign_tree.column('date', width=80, anchor='e')
        self.cust_assign_tree.tag_configure('paid', foreground='green')
        self.cust_assign_tree.pack(fill='both', expand=True, padx=6, pady=6)
        self.cust_assign_tree.bind('<Button-3>', self.on_assignment_right)

        bottom = tb.Frame(self.cust_frame)
        bottom.pack(fill='x')
        tb.Button(bottom, text='+ إضافة مبلغ مخصص', bootstyle='primary', command=self.add_assignment_for_customer).pack(side=LEFT, padx=6, pady=6)
        tb.Button(bottom, text='+ إضافة دفعة مدفوعة', bootstyle='success', command=self.add_payment_for_customer).pack(side=LEFT, padx=6, pady=6)

    # Loading and handlers
    def load_all(self):
        self.load_workers()
        self.load_importers()
        self.load_customer()
        # Re-select current worker/importer to refresh their assignments
        if self.selected_worker:
            try:
                self.workers_tree.selection_set(self.selected_worker)
                self.on_worker_select(None)
            except Exception:
                pass
        if self.selected_importer:
            try:
                self.imp_tree.selection_set(self.selected_importer)
                self.on_importer_select(None)
            except Exception:
                pass
        # Trigger callback to refresh parent window
        if self.on_update_callback:
            try:
                self.on_update_callback()
            except Exception:
                pass

    def load_workers(self):
        for i in self.workers_tree.get_children():
            self.workers_tree.delete(i)
        workers = self.db.get_workers_by_project(self.project_id)
        for w in workers:
            self.workers_tree.insert('', 'end', iid=w['id'], values=(w.get('job') or '', w['name']))

    def load_importers(self):
        for i in self.imp_tree.get_children():
            self.imp_tree.delete(i)
        imps = self.db.get_importers_by_project(self.project_id)
        for it in imps:
            self.imp_tree.insert('', 'end', iid=it['id'], values=(it.get('job') or '', it['name']))

    def load_customer(self):
        # calculate summary for customer only
        try:
            total, paid = self.db.get_customer_summary(self.project_id)
        except Exception:
            total = 0
            paid = 0
        remain = total - paid
        self.cust_summary.config(text=f'إجمالي: {total:.2f}    المدفوع: {paid:.2f}    المتبقي: {remain:.2f}')

        for i in self.cust_assign_tree.get_children():
            self.cust_assign_tree.delete(i)
        assigns = self.db.get_assignments('customer', self.project_id)
        for a in assigns:
            self.cust_assign_tree.insert('', 'end', iid=f"a{a['id']}", values=(f"{a['amount']:.2f}", a['date']))
            # add payments as children
            pays = self.db.get_payments(a['id'])
            for p in pays:
                self.cust_assign_tree.insert(f"a{a['id']}", 'end', iid=f"p{p['id']}", values=(f"{p['amount']:.2f}", p['date']), tags=('paid',))
        # Auto-expand all parent rows
        self.expand_all_rows(self.cust_assign_tree)

    def add_worker(self):
        try:
            # Get existing worker names for autocomplete
            existing_names = self.db.get_unique_worker_names()
            
            # Show autocomplete dialog for name selection with auto-select
            dialog = AutocompleteDialog(
                self.win, 
                'إضافة عامل', 
                'اسم العامل:',
                existing_names,
                auto_select=True
            )
            
            name = dialog.result_name
            if not name:
                return
            
            # Check if this worker+job combination already exists in this project
            workers_in_project = self.db.get_workers_by_project(self.project_id)
            
            # Ask for job (required)
            existing_jobs = self.db.get_unique_jobs_for_worker(name)
            
            job_dialog = AutocompleteDialog(
                self.win, 
                'اختر المهنة', 
                'المهنة:',
                existing_jobs,
                auto_select=True,
                is_job=True
            )
            job = job_dialog.result_name
            if not job:
                return
            
            # Check if worker+job combination already exists in this project
            if any(w['name'] == name and w.get('job') == job for w in workers_in_project):
                messagebox.showerror('خطأ', 'هذا العامل مع هذه المهنة موجود بالفعل في هذا المشروع!', parent=self.win)
                return
            
            # Check if worker+job exists in other projects
            existing_worker_ids = self.db.get_worker_ids_by_name_and_job(name, job)
            
            if existing_worker_ids:
                # Worker with same job exists in another project - ask user if they want to link it
                response = messagebox.askyesno(
                    'عامل موجود',
                    f'هذا العامل "{name}" مع المهنة "{job}"\nموجود بالفعل في مشروع آخر.\n\nهل تريد إضافتـــه إلى هذا المشروع أيضاً؟',
                    parent=self.win
                )
                
                if response:
                    # Add the existing worker to this project
                    wid = self.db.add_worker_with_job(self.project_id, name, job)
                else:
                    return
            else:
                # New worker+job combination
                wid = self.db.add_worker_with_job(self.project_id, name, job)
            
            self.load_workers()
            if self.on_update_callback:
                self.on_update_callback()
        except Exception as e:
            messagebox.showerror('خطأ', f'حدث خطأ أثناء الاتصال بقاعدة البيانات: {str(e)}', parent=self.win)

    def on_worker_right(self, event):
        iid = self.workers_tree.identify_row(event.y)
        if not iid:
            return
        menu = tb.Menu(self.win, tearoff=0)
        menu.add_command(label='تعديل الاسم', command=lambda: self.edit_worker(iid))
        menu.add_command(label='حذف', command=lambda: self.delete_worker(iid))
        menu.tk_popup(event.x_root, event.y_root)

    def edit_worker(self, worker_id):
        try:
            cur = self.db.get_workers_by_project(self.project_id)
            w = next((x for x in cur if x['id'] == int(worker_id)), None)
            if not w:
                return
            name = self.ask_string_focused('تعديل العامل', 'الاسم:', initialvalue=w['name'])
            if name:
                self.db.edit_worker(worker_id, name)
                self.load_workers()
                if self.on_update_callback:
                    self.on_update_callback()
        except Exception:
            messagebox.showerror('خطأ', 'حدث خطأ أثناء الاتصال بقاعدة البيانات.', parent=self.win)

    def delete_worker(self, worker_id):
        if messagebox.askyesno('تأكيد', 'حذف العامل؟', parent=self.win):
            try:
                # Delete all assignments and payments for this worker
                assigns = self.db.get_assignments('worker', worker_id)
                for a in assigns:
                    payments = self.db.get_payments(a['id'])
                    for p in payments:
                        self.db.delete_payment(p['id'])
                    self.db.delete_assignment(a['id'])
                # Now delete the worker
                self.db.delete_worker(worker_id)
                # Clear selected worker since it's deleted
                if self.selected_worker == worker_id:
                    self.selected_worker = None
                    # Clear assignments tree
                    for i in self.assign_tree.get_children():
                        self.assign_tree.delete(i)
                self.load_workers()
                if self.on_update_callback:
                    self.on_update_callback()
            except Exception:
                messagebox.showerror('خطأ', 'حدث خطأ أثناء الاتصال بقاعدة البيانات.', parent=self.win)

    def on_worker_select(self, _ev):
        sel = self.workers_tree.selection()
        if not sel:
            self.selected_worker = None
            return
        wid = sel[0]
        self.selected_worker = wid
        self.load_assignments_for('worker', int(wid))

    def load_assignments_for(self, entity_type, entity_id):
        tree = self.assign_tree if entity_type == 'worker' else self.imp_assign_tree
        for i in tree.get_children():
            tree.delete(i)
        assigns = self.db.get_assignments(entity_type, entity_id)
        for a in assigns:
            tree.insert('', 'end', iid=f"a{a['id']}", values=(a.get('description') or '', f"{a['amount']:.2f}", a['date']))
            pays = self.db.get_payments(a['id'])
            for p in pays:
                tree.insert(f"a{a['id']}", 'end', iid=f"p{p['id']}", values=('', f"{p['amount']:.2f}", p['date']), tags=('paid',))
        # Auto-expand all parent rows
        self.expand_all_rows(tree)

    def add_assignment_for_worker(self):
        sel = self.workers_tree.selection()
        if not sel:
            messagebox.showwarning('تنبيه', 'اختر عامل أولاً', parent=self.win)
            return
        wid = int(sel[0])
        try:
            amt = simpledialog.askstring('مبلغ مخصص', 'المبلغ:', parent=self.win)
            if not amt:
                return
            amt_v = validate_amount(amt)
            desc = simpledialog.askstring('وصف العمل', 'وصف العمل المنجز:', parent=self.win)
            from datetime import datetime
            date_v = datetime.now().strftime('%d-%m-%Y')
            self.db.add_assignment('worker', wid, amt_v, date_v, desc or '')
            # Reload assignments for this worker immediately
            self.load_assignments_for('worker', wid)
            # Also reload customer summary
            self.load_customer()
            if self.on_update_callback:
                self.on_update_callback()
        except Exception as e:
            messagebox.showerror('خطأ', str(e), parent=self.win)

    # Importers handlers
    def add_importer(self):
        try:
            # Get existing importer names for autocomplete
            existing_names = self.db.get_unique_importer_names()
            
            # Show autocomplete dialog for name selection with auto-select
            dialog = AutocompleteDialog(
                self.win, 
                'إضافة مورد', 
                'اسم المورد:',
                existing_names,
                auto_select=True
            )
            
            name = dialog.result_name
            if not name:
                return
            
            # Check if this importer+job combination already exists in this project
            importers_in_project = self.db.get_importers_by_project(self.project_id)
            
            # Ask for job/item (required)
            existing_jobs = self.db.get_unique_jobs_for_importer(name)
            
            job_dialog = AutocompleteDialog(
                self.win, 
                'اختر السلعة/الوظيفة', 
                'السلعة/الوظيفة:',
                existing_jobs,
                auto_select=True,
                is_job=True
            )
            job = job_dialog.result_name
            if not job:
                return
            
            # Check if importer+job combination already exists in this project
            if any(i['name'] == name and i.get('job') == job for i in importers_in_project):
                messagebox.showerror('خطأ', 'هذا المورد مع هذه السلعة موجود بالفعل في هذا المشروع!', parent=self.win)
                return
            
            # Check if importer+job exists in other projects
            existing_importer_ids = self.db.get_importer_ids_by_name_and_job(name, job)
            
            if existing_importer_ids:
                # Importer with same job exists in another project - ask user if they want to link it
                response = messagebox.askyesno(
                    'مورد موجود',
                    f'هذا المورد "{name}" مع السلعة "{job}"\nموجود بالفعل في مشروع آخر.\n\nهل تريد إضافتـــه إلى هذا المشروع أيضاً؟',
                    parent=self.win
                )
                
                if response:
                    # Add the existing importer to this project
                    iid = self.db.add_importer_with_job(self.project_id, name, job)
                else:
                    return
            else:
                # New importer+job combination
                iid = self.db.add_importer_with_job(self.project_id, name, job)
            
            self.load_importers()
            if self.on_update_callback:
                self.on_update_callback()
        except Exception as e:
            messagebox.showerror('خطأ', f'حدث خطأ أثناء الاتصال بقاعدة البيانات: {str(e)}', parent=self.win)

    def on_importer_right(self, event):
        iid = self.imp_tree.identify_row(event.y)
        if not iid:
            return
        menu = tb.Menu(self.win, tearoff=0)
        menu.add_command(label='تعديل الاسم', command=lambda: self.edit_importer(iid))
        menu.add_command(label='حذف', command=lambda: self.delete_importer(iid))
        menu.tk_popup(event.x_root, event.y_root)

    def edit_importer(self, importer_id):
        try:
            cur = self.db.get_importers_by_project(self.project_id)
            w = next((x for x in cur if x['id'] == int(importer_id)), None)
            if not w:
                return
            name = self.ask_string_focused('تعديل المورد', 'الاسم:', initialvalue=w['name'])
            if name:
                self.db.edit_importer(importer_id, name)
                self.load_importers()
                if self.on_update_callback:
                    self.on_update_callback()
        except Exception:
            messagebox.showerror('خطأ', 'حدث خطأ أثناء الاتصال بقاعدة البيانات.', parent=self.win)

    def delete_importer(self, importer_id):
        if messagebox.askyesno('تأكيد', 'حذف المورد؟', parent=self.win):
            try:
                # Delete all assignments and payments for this importer
                assigns = self.db.get_assignments('importer', importer_id)
                for a in assigns:
                    payments = self.db.get_payments(a['id'])
                    for p in payments:
                        self.db.delete_payment(p['id'])
                    self.db.delete_assignment(a['id'])
                # Now delete the importer
                self.db.delete_importer(importer_id)
                # Clear selected importer since it's deleted
                if self.selected_importer == importer_id:
                    self.selected_importer = None
                    # Clear assignments tree
                    for i in self.imp_assign_tree.get_children():
                        self.imp_assign_tree.delete(i)
                self.load_importers()
                if self.on_update_callback:
                    self.on_update_callback()
            except Exception:
                messagebox.showerror('خطأ', 'حدث خطأ أثناء الاتصال بقاعدة البيانات.', parent=self.win)

    def on_importer_select(self, _ev):
        sel = self.imp_tree.selection()
        if not sel:
            self.selected_importer = None
            return
        iid = sel[0]
        self.selected_importer = iid
        self.load_assignments_for('importer', int(iid))

    def add_assignment_for_importer(self):
        sel = self.imp_tree.selection()
        if not sel:
            messagebox.showwarning('تنبيه', 'اختر مورد أولاً', parent=self.win)
            return
        iid = int(sel[0])
        try:
            amt = simpledialog.askstring('مبلغ مخصص', 'المبلغ:', parent=self.win)
            if not amt:
                return
            amt_v = validate_amount(amt)
            desc = simpledialog.askstring('وصف العمل', 'وصف العمل المنجز:', parent=self.win)
            from datetime import datetime
            date_v = datetime.now().strftime('%d-%m-%Y')
            self.db.add_assignment('importer', iid, amt_v, date_v, desc or '')
            # Reload assignments for this importer immediately
            self.load_assignments_for('importer', iid)
            # Also reload customer summary
            self.load_customer()
            if self.on_update_callback:
                self.on_update_callback()
        except Exception as e:
            messagebox.showerror('خطأ', str(e), parent=self.win)

    # Assignment right-click (edit/delete) -- simple implementation
    def on_assignment_right(self, event):
        widget = event.widget
        iid = widget.identify_row(event.y)
        if not iid:
            return
        menu = tb.Menu(self.win, tearoff=0)
        # Add payment and delete options
        menu.add_command(label='إضافة دفعة', command=lambda: self.add_payment_for_assignment(widget, iid))
        
        # Check if it's a child payment row (starts with 'p')
        if not (isinstance(iid, str) and iid.startswith('p')):
            # Only show delete for assignment rows, not payment rows
            menu.add_command(label='حذف السجل', command=lambda: self.delete_assignment(widget, iid))
        else:
            # For payment rows, offer delete payment
            menu.add_command(label='حذف الدفعة', command=lambda: self.delete_payment_row(widget, iid))
        
        menu.tk_popup(event.x_root, event.y_root)

    def delete_assignment(self, widget, aid):
        if messagebox.askyesno('تأكيد', 'حذف السجل؟', parent=self.win):
            try:
                # Extract the real assignment id (remove 'a' prefix if present)
                if isinstance(aid, str) and aid.startswith('a'):
                    real_aid = int(aid[1:])
                else:
                    real_aid = int(aid)
                
                self.db.delete_assignment(real_aid)
                self.load_all()
            except Exception as e:
                messagebox.showerror('خطأ', 'حدث خطأ أثناء الحذف', parent=self.win)

    def delete_payment_row(self, widget, iid):
        if messagebox.askyesno('تأكيد', 'حذف الدفعة؟', parent=self.win):
            try:
                # Extract payment id (remove 'p' prefix)
                if isinstance(iid, str) and iid.startswith('p'):
                    payment_id = int(iid[1:])
                else:
                    return
                
                self.db.delete_payment(payment_id)
                self.load_all()
            except Exception as e:
                messagebox.showerror('خطأ', 'حدث خطأ أثناء حذف الدفعة', parent=self.win)

    # Customer actions
    def add_assignment_for_customer(self):
        try:
            amt = simpledialog.askstring('مبلغ مخصص من العميل', 'المبلغ:', parent=self.win)
            if not amt:
                return
            amt_v = validate_amount(amt)
            desc = simpledialog.askstring('وصف العمل', 'وصف العمل المنجز:', parent=self.win)
            from datetime import datetime
            date_v = datetime.now().strftime('%d-%m-%Y')
            self.db.add_assignment('customer', self.project_id, amt_v, date_v, desc or '')
            self.load_customer()
            if self.on_update_callback:
                self.on_update_callback()
        except Exception as e:
            messagebox.showerror('خطأ', str(e), parent=self.win)

    def add_payment_for_customer(self):
        try:
            # choose assignment from customer assignments
            assigns = self.db.get_assignments('customer', self.project_id)
            if not assigns:
                messagebox.showwarning('تنبيه', 'لا يوجد مبالغ مرجعية')
                return
            # pick first for simplicity or ask user to input assignment id
            aid = assigns[0]['id']
            amt = simpledialog.askstring('إضافة دفعة', 'المبلغ:')
            if not amt:
                return
            amt_v = validate_amount(amt)
            from datetime import datetime
            date_v = datetime.now().strftime('%d-%m-%Y')
            self.db.add_payment(aid, amt_v, date_v)
            self.load_customer()
        except Exception as e:
            messagebox.showerror('خطأ', str(e), parent=self.win)

    def add_payment_for_assignment(self, widget, iid):
        # iid may be like 'a{assignment_id}' for customer, or numeric for worker/importer assignments
        try:
            # if a payment child was clicked, get its parent assignment
            if isinstance(iid, str) and iid.startswith('p'):
                try:
                    iid = widget.parent(iid)
                except Exception:
                    return
            # normalize to assignment id
            if isinstance(iid, str) and iid.startswith('a'):
                aid = int(iid[1:])
            else:
                # numeric id
                try:
                    aid = int(iid)
                except Exception:
                    # might be child payment id like 'p{id}'
                    if isinstance(iid, str) and iid.startswith('p'):
                        return
                    return
            amt = simpledialog.askstring('إضافة دفعة', 'المبلغ:')
            if not amt:
                return
            amt_v = validate_amount(amt)
            from datetime import datetime
            date_v = datetime.now().strftime('%d-%m-%Y')
            self.db.add_payment(aid, amt_v, date_v)
            # reload the corresponding tree
            # try reload in all
            self.load_all()
        except Exception as e:
            messagebox.showerror('خطأ', str(e), parent=self.win)

    def add_payment_for_selected_worker_assignment(self):
        sel = self.assign_tree.selection()
        if not sel:
            messagebox.showwarning('تنبيه', 'اختر مبلغاً مخصصاً أولاً', parent=self.win)
            return
        iid = sel[0]
        self.add_payment_for_assignment(self.assign_tree, iid)

    def add_payment_for_selected_importer_assignment(self):
        sel = self.imp_assign_tree.selection()
        if not sel:
            messagebox.showwarning('تنبيه', 'اختر مبلغاً مخصصاً أولاً', parent=self.win)
            return
        iid = sel[0]
        self.add_payment_for_assignment(self.imp_assign_tree, iid)

    def expand_all_rows(self, tree):
        """Expand all parent rows in tree to show child payments"""
        for item in tree.get_children():
            try:
                tree.item(item, open=True)
            except Exception:
                pass

class WorkerDetailWindow:
    """Detail window for a specific worker showing all projects they work on"""
    def __init__(self, db, entity_type, entity_ids, entity_name, on_update_callback=None):
        """
        entity_type: 'worker' or 'importer'
        entity_ids: ID or list of IDs of the worker/importer (can appear in multiple projects)
        entity_name: Name of the worker/importer
        """
        self.db = db
        self.entity_type = entity_type
        # Ensure entity_ids is a list
        if not isinstance(entity_ids, list):
            entity_ids = [entity_ids]
        self.entity_ids = entity_ids
        self.entity_name = entity_name
        self.on_update = on_update_callback or (lambda: None)
        
        self.win = Toplevel()
        self.win.title(f'تفاصيل ال{"عامل" if entity_type == "worker" else "مورد"}: {entity_name}')
        self.win.geometry('900x600')
        self.win.option_add('*Font', 'SegoeUI 10')
        
        self._build_ui()
        self.load_data()
    
    def _build_ui(self):
        # Header with worker/importer info
        header = tb.Frame(self.win)
        header.pack(fill='x', padx=12, pady=(8, 6))
        
        title = tb.Label(header, text=f'{"العامل" if self.entity_type == "worker" else "المورد"}: {self.entity_name}',
                        font=('Segoe UI', 14, 'bold'), anchor='e')
        title.pack(side='right', fill='both', expand=True)
        
        # Get current totals for display (sum across all entity IDs)
        total_assigned = 0
        total_paid = 0
        
        for entity_id in self.entity_ids:
            assignments = self.db.get_assignments(self.entity_type, entity_id)
            total_assigned += sum(a['amount'] for a in assignments)
            
            # Calculate total paid for this entity
            for a in assignments:
                cur = self.db.conn.cursor()
                cur.execute('SELECT SUM(amount) as s FROM payments WHERE assignment_id=?', (a['id'],))
                s = cur.fetchone()['s'] or 0
                total_paid += s
        
        stats = tb.Label(header, text=f'المجموع المُكلّف: {total_assigned:.2f} | المدفوع: {total_paid:.2f} | المتبقي: {total_assigned - total_paid:.2f}',
                        anchor='e', font=('Segoe UI', 9))
        stats.pack(side='right', padx=(0, 12))
        
        # Main frame for content
        main = tb.Frame(self.win)
        main.pack(fill='both', expand=True, padx=12, pady=(6, 12))
        
        # Tree for assignments by project (columns reversed for RTL: date, amount, description, project)
        columns = ('date', 'amount', 'description', 'project')
        self.tree = tb.Treeview(main, columns=columns, show='headings', height=20)
        
        self.tree.heading('date', text='التاريخ', anchor='e')
        self.tree.heading('amount', text='المبلغ', anchor='e')
        self.tree.heading('description', text='وصف العمل', anchor='e')
        self.tree.heading('project', text='المشروع', anchor='e')
        
        self.tree.column('date', width=80, anchor='e')
        self.tree.column('amount', width=80, anchor='e')
        self.tree.column('description', width=200, anchor='e')
        self.tree.column('project', width=150, anchor='e')
        
        self.tree.tag_configure('paid', foreground='green')
        self.tree.pack(fill='both', expand=True)
        
        # Add mouse wheel scrolling to tree with improved handling
        def _on_mousewheel(event):
            # Ensure tree has focus for smooth scrolling
            self.tree.focus_set()
            
            # Handle Windows and Linux mouse wheel events
            try:
                if event.num == 5 or event.delta < 0:
                    self.tree.yview_scroll(3, "units")
                elif event.num == 4 or event.delta > 0:
                    self.tree.yview_scroll(-3, "units")
            except Exception:
                pass
        
        # Bind to tree and main window
        self.tree.bind("<MouseWheel>", _on_mousewheel)
        self.tree.bind("<Button-4>", _on_mousewheel)
        self.tree.bind("<Button-5>", _on_mousewheel)
        main.bind("<MouseWheel>", _on_mousewheel)
        main.bind("<Button-4>", _on_mousewheel)
        main.bind("<Button-5>", _on_mousewheel)
        
        # Buttons
        btn_frame = tb.Frame(self.win)
        btn_frame.pack(fill='x', padx=12, pady=(6, 12))
        
        tb.Button(btn_frame, text='حذف', bootstyle='danger-outline', 
                 command=lambda: self.delete_assignment(self.tree)).pack(side=LEFT, padx=6)
        
        tb.Button(btn_frame, text='إغلاق', bootstyle='secondary-outline',
                 command=self.win.destroy).pack(side=LEFT, padx=6)
    
    def load_data(self):
        """Load all assignments for this worker/importer grouped by project"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        assignments = self.db.get_assignments(self.entity_type, self.entity_id)
        
        # Group by project_id
        from collections import defaultdict
        by_project = defaultdict(list)
        
        for a in assignments:
            # Get project info for this assignment
            cur = self.db.conn.cursor()
            # The assignment doesn't directly have project_id, so we get it from worker/importer
            if self.entity_type == 'worker':
                cur.execute('SELECT project_id FROM workers WHERE id=?', (self.entity_id,))
            else:
                cur.execute('SELECT project_id FROM importers WHERE id=?', (self.entity_id,))
            
            row = cur.fetchone()
            project_id = row['project_id'] if row else None
            
            if project_id:
                # Get project name
                proj = next((p for p in self.db.get_all_projects() if p['id'] == project_id), None)
                proj_name = proj['name'] if proj else f'Unknown (ID: {project_id})'
                by_project[project_id].append({
                    'project_name': proj_name,
                    'assignment': a
                })
        
        # Display by project
        for project_id in sorted(by_project.keys(), key=lambda x: by_project[x][0]['project_name']):
            items = by_project[project_id]
            proj_name = items[0]['project_name']
            
            # Add project parent row (expanded by default)
            parent_iid = self.tree.insert('', 'end', text=proj_name,
                                         values=('', '', '', proj_name),
                                         tags=())
            
            # Expand parent by default
            self.tree.item(parent_iid, open=True)
            
            # Add assignment rows as children
            for item in items:
                a = item['assignment']
                
                # Calculate paid amount for this assignment
                cur = self.db.conn.cursor()
                cur.execute('SELECT SUM(amount) as s FROM payments WHERE assignment_id=?', (a['id'],))
                paid = cur.fetchone()['s'] or 0
                
                # Add row for assigned amount
                amount_text = f"{a['amount']:.2f}"
                
                assign_iid = self.tree.insert(parent_iid, 'end', iid=str(a['id']),
                               values=(a['date'], amount_text, a.get('description') or '', ''),
                               tags=())
                
                # Expand assignment row by default to show paid amounts
                if paid > 0:
                    self.tree.item(assign_iid, open=True)
                
                # Add sub-row for paid amount (in green)
                if paid > 0:
                    paid_text = f'{paid:.2f}'
                    self.tree.insert(str(a['id']), 'end',
                                   values=(a['date'], paid_text, f'تم دفع: {a.get("description") or ""}', ''),
                                   tags=('paid',))
    
    def delete_assignment(self, tree):
        """Delete selected assignment"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning('تنبيه', 'اختر مبلغاً مخصصاً أولاً', parent=self.win)
            return
        
        iid = selection[0]
        try:
            assignment_id = int(iid)
            if messagebox.askyesno('تأكيد', 'هل تريد حذف هذا المبلغ المخصص؟', parent=self.win):
                self.db.delete_assignment(assignment_id)
                self.load_data()
        except ValueError:
            pass  # Parent row selected