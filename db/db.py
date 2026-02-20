import sqlite3
from datetime import datetime


class Database:
    def __init__(self, path='data.db'):
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        cur = self.conn.cursor()
        cur.executescript('''
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT,
            total_assigned REAL DEFAULT 0,
            total_paid REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            name TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS importers (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            name TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY,
            entity_type TEXT CHECK(entity_type IN ('worker','importer','customer')),
            entity_id INTEGER,
            amount REAL,
            date TEXT,
            description TEXT DEFAULT '',
            good TEXT
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY,
            assignment_id INTEGER,
            amount REAL,
            date TEXT,
            FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
        );
        ''')
        self.conn.commit()
        # Ensure optional columns exist (job for workers only)
        cur.execute("PRAGMA table_info(workers)")
        cols = [r[1] for r in cur.fetchall()]
        if 'job' not in cols:
            cur.execute('ALTER TABLE workers ADD COLUMN job TEXT')
        # Add good column to assignments if it doesn't exist
        cur.execute("PRAGMA table_info(assignments)")
        cols = [r[1] for r in cur.fetchall()]
        if 'description' not in cols:
            cur.execute('ALTER TABLE assignments ADD COLUMN description TEXT DEFAULT ""')
        if 'good' not in cols:
            cur.execute('ALTER TABLE assignments ADD COLUMN good TEXT')
        self.conn.commit()

    # Projects
    def add_project(self, name):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO projects(name) VALUES(?)', (name,))
        self.conn.commit()
        return cur.lastrowid

    def edit_project(self, project_id, new_name):
        cur = self.conn.cursor()
        cur.execute('UPDATE projects SET name=? WHERE id=?', (new_name, project_id))
        self.conn.commit()

    def delete_project(self, project_id):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM projects WHERE id=?', (project_id,))
        self.conn.commit()

    def get_all_projects(self):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM projects ORDER BY id DESC')
        return [dict(row) for row in cur.fetchall()]

    # Workers / Importers
    def add_worker(self, project_id, name):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO workers(project_id, name) VALUES(?,?)', (project_id, name))
        self.conn.commit()
        return cur.lastrowid

    def add_worker_with_job(self, project_id, name, job=None):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO workers(project_id, name, job) VALUES(?,?,?)', (project_id, name, job))
        self.conn.commit()
        return cur.lastrowid

    def edit_worker(self, worker_id, new_name):
        cur = self.conn.cursor()
        cur.execute('UPDATE workers SET name=? WHERE id=?', (new_name, worker_id))
        self.conn.commit()

    def delete_worker(self, worker_id):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM workers WHERE id=?', (worker_id,))
        self.conn.commit()

    def get_workers_by_project(self, project_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM workers WHERE project_id=?', (project_id,))
        return [dict(r) for r in cur.fetchall()]

    def add_importer(self, project_id, name):
        """Add importer with only name (job is now tracked in assignments)"""
        cur = self.conn.cursor()
        cur.execute('INSERT INTO importers(project_id, name) VALUES(?,?)', (project_id, name))
        self.conn.commit()
        return cur.lastrowid

    def add_importer_with_job(self, project_id, name, job=None):
        """Backwards compatible method - job parameter is ignored, use add_importer instead"""
        return self.add_importer(project_id, name)

    def edit_importer(self, importer_id, new_name):
        cur = self.conn.cursor()
        cur.execute('UPDATE importers SET name=? WHERE id=?', (new_name, importer_id))
        self.conn.commit()

    def delete_importer(self, importer_id):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM importers WHERE id=?', (importer_id,))
        self.conn.commit()

    def get_importers_by_project(self, project_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM importers WHERE project_id=?', (project_id,))
        return [dict(r) for r in cur.fetchall()]

    # Assignments
    def add_assignment(self, entity_type, entity_id, amount, date, description='', good=None):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO assignments(entity_type, entity_id, amount, date, description, good) VALUES(?,?,?,?,?,?)',
                    (entity_type, entity_id, amount, date, description, good))
        self.conn.commit()
        aid = cur.lastrowid
        # recalc affected project(s)
        self._recalc_projects_for_assignment(entity_type, entity_id)
        return aid

    def delete_assignment(self, assignment_id):
        cur = self.conn.cursor()
        # find related entity to recalc after deletion
        cur.execute('SELECT entity_type, entity_id FROM assignments WHERE id=?', (assignment_id,))
        row = cur.fetchone()
        cur.execute('DELETE FROM assignments WHERE id=?', (assignment_id,))
        self.conn.commit()
        if row:
            self._recalc_projects_for_assignment(row['entity_type'], row['entity_id'])

    def get_assignments(self, entity_type, entity_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM assignments WHERE entity_type=? AND entity_id=? ORDER BY id DESC',
                    (entity_type, entity_id))
        return [dict(r) for r in cur.fetchall()]

    # Payments
    def add_payment(self, assignment_id, amount, date):
        cur = self.conn.cursor()
        # enforce that payments for this assignment do not exceed assignment.amount
        cur.execute('SELECT amount FROM assignments WHERE id=?', (assignment_id,))
        ar = cur.fetchone()
        if not ar:
            raise ValueError('السجل المرجعي غير موجود')
        assign_amount = ar['amount']
        cur.execute('SELECT SUM(amount) as s FROM payments WHERE assignment_id=?', (assignment_id,))
        paid_sum = cur.fetchone()['s'] or 0
        if (paid_sum + float(amount)) > float(assign_amount) + 1e-9:
            raise ValueError('المبلغ المدفوع يتجاوز المبلغ المكلّف')
        cur.execute('INSERT INTO payments(assignment_id, amount, date) VALUES(?,?,?)', (assignment_id, amount, date))
        self.conn.commit()
        # recalc project via lookup
        cur.execute('SELECT entity_type, entity_id FROM assignments WHERE id=?', (assignment_id,))
        row = cur.fetchone()
        if row:
            self._recalc_projects_for_assignment(row['entity_type'], row['entity_id'])
        return cur.lastrowid

    def delete_payment(self, payment_id):
        cur = self.conn.cursor()
        # find assignment id
        cur.execute('SELECT assignment_id FROM payments WHERE id=?', (payment_id,))
        r = cur.fetchone()
        cur.execute('DELETE FROM payments WHERE id=?', (payment_id,))
        self.conn.commit()
        if r:
            cur.execute('SELECT entity_type, entity_id FROM assignments WHERE id=?', (r['assignment_id'],))
            row = cur.fetchone()
            if row:
                self._recalc_projects_for_assignment(row['entity_type'], row['entity_id'])

    def get_payments(self, assignment_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM payments WHERE assignment_id=? ORDER BY id DESC', (assignment_id,))
        return [dict(r) for r in cur.fetchall()]

    def get_customer_summary(self, project_id):
        cur = self.conn.cursor()
        cur.execute('SELECT SUM(amount) as s FROM assignments WHERE entity_type="customer" AND entity_id=?', (project_id,))
        total = cur.fetchone()['s'] or 0
        # get payments for those assignments
        cur.execute('SELECT id FROM assignments WHERE entity_type="customer" AND entity_id=?', (project_id,))
        aids = [r['id'] for r in cur.fetchall()]
        paid = 0
        if aids:
            q = f"SELECT SUM(amount) as s FROM payments WHERE assignment_id IN ({','.join(['?']*len(aids))})"
            cur.execute(q, aids)
            paid = cur.fetchone()['s'] or 0
        return float(total), float(paid)

    # Helpers
    def _recalc_projects_for_assignment(self, entity_type, entity_id):
        # find associated project id(s)
        project_ids = set()
        cur = self.conn.cursor()
        if entity_type == 'customer':
            project_ids.add(int(entity_id))
        elif entity_type == 'worker':
            cur.execute('SELECT project_id FROM workers WHERE id=?', (entity_id,))
            r = cur.fetchone()
            if r:
                project_ids.add(r['project_id'])
        elif entity_type == 'importer':
            cur.execute('SELECT project_id FROM importers WHERE id=?', (entity_id,))
            r = cur.fetchone()
            if r:
                project_ids.add(r['project_id'])

        for pid in project_ids:
            self._recalc_project(pid)

    def _recalc_project(self, project_id):
        cur = self.conn.cursor()
        # total assigned: sum assignments for customer with entity_id=project_id
        cur.execute('SELECT SUM(amount) as s FROM assignments WHERE entity_type="customer" AND entity_id=?', (project_id,))
        s1 = cur.fetchone()['s'] or 0

        # plus assignments for workers/importers that belong to this project
        cur.execute('SELECT id FROM workers WHERE project_id=?', (project_id,))
        worker_ids = [r['id'] for r in cur.fetchall()]
        cur.execute('SELECT id FROM importers WHERE project_id=?', (project_id,))
        importer_ids = [r['id'] for r in cur.fetchall()]

        s2 = 0
        if worker_ids:
            q = f"SELECT SUM(amount) as s FROM assignments WHERE entity_type='worker' AND entity_id IN ({','.join(['?']*len(worker_ids))})"
            cur.execute(q, worker_ids)
            s2 += cur.fetchone()['s'] or 0
        if importer_ids:
            q = f"SELECT SUM(amount) as s FROM assignments WHERE entity_type='importer' AND entity_id IN ({','.join(['?']*len(importer_ids))})"
            cur.execute(q, importer_ids)
            s2 += cur.fetchone()['s'] or 0

        total_assigned = (s1 or 0) + (s2 or 0)

        # total paid: sum of payments linked to those assignments
        # collect relevant assignment ids
        assignment_ids = []
        cur.execute('SELECT id FROM assignments WHERE entity_type="customer" AND entity_id=?', (project_id,))
        assignment_ids += [r['id'] for r in cur.fetchall()]
        if worker_ids:
            if len(worker_ids) == 1:
                cur.execute('SELECT id FROM assignments WHERE entity_type="worker" AND entity_id=?', (worker_ids[0],))
                assignment_ids += [r['id'] for r in cur.fetchall()]
            else:
                q = f"SELECT id FROM assignments WHERE entity_type='worker' AND entity_id IN ({','.join(['?']*len(worker_ids))})"
                cur.execute(q, worker_ids)
                assignment_ids += [r['id'] for r in cur.fetchall()]
        if importer_ids:
            if len(importer_ids) == 1:
                cur.execute('SELECT id FROM assignments WHERE entity_type="importer" AND entity_id=?', (importer_ids[0],))
                assignment_ids += [r['id'] for r in cur.fetchall()]
            else:
                q = f"SELECT id FROM assignments WHERE entity_type='importer' AND entity_id IN ({','.join(['?']*len(importer_ids))})"
                cur.execute(q, importer_ids)
                assignment_ids += [r['id'] for r in cur.fetchall()]

        total_paid = 0
        if assignment_ids:
            q = f"SELECT SUM(amount) as s FROM payments WHERE assignment_id IN ({','.join(['?']*len(assignment_ids))})"
            cur.execute(q, assignment_ids)
            total_paid = cur.fetchone()['s'] or 0

        cur.execute('UPDATE projects SET total_assigned=?, total_paid=? WHERE id=?', (total_assigned, total_paid, project_id))
        self.conn.commit()
    def get_workers_importers_summary(self, project_id):
        """Get total assigned and paid for workers+importers only (excluding customer)"""
        cur = self.conn.cursor()
        
        # Get worker and importer ids
        cur.execute('SELECT id FROM workers WHERE project_id=?', (project_id,))
        worker_ids = [r['id'] for r in cur.fetchall()]
        cur.execute('SELECT id FROM importers WHERE project_id=?', (project_id,))
        importer_ids = [r['id'] for r in cur.fetchall()]
        
        # Total assigned for workers+importers
        total_assigned = 0
        if worker_ids:
            if len(worker_ids) == 1:
                cur.execute('SELECT SUM(amount) as s FROM assignments WHERE entity_type="worker" AND entity_id=?', (worker_ids[0],))
                total_assigned += cur.fetchone()['s'] or 0
            else:
                q = f"SELECT SUM(amount) as s FROM assignments WHERE entity_type='worker' AND entity_id IN ({','.join(['?']*len(worker_ids))})"
                cur.execute(q, worker_ids)
                total_assigned += cur.fetchone()['s'] or 0
        
        if importer_ids:
            if len(importer_ids) == 1:
                cur.execute('SELECT SUM(amount) as s FROM assignments WHERE entity_type="importer" AND entity_id=?', (importer_ids[0],))
                total_assigned += cur.fetchone()['s'] or 0
            else:
                q = f"SELECT SUM(amount) as s FROM assignments WHERE entity_type='importer' AND entity_id IN ({','.join(['?']*len(importer_ids))})"
                cur.execute(q, importer_ids)
                total_assigned += cur.fetchone()['s'] or 0
        
        # Total paid for workers+importers
        total_paid = 0
        assignment_ids = []
        if worker_ids:
            if len(worker_ids) == 1:
                cur.execute('SELECT id FROM assignments WHERE entity_type="worker" AND entity_id=?', (worker_ids[0],))
            else:
                q = f"SELECT id FROM assignments WHERE entity_type='worker' AND entity_id IN ({','.join(['?']*len(worker_ids))})"
                cur.execute(q, worker_ids)
            assignment_ids += [r['id'] for r in cur.fetchall()]
        
        if importer_ids:
            if len(importer_ids) == 1:
                cur.execute('SELECT id FROM assignments WHERE entity_type="importer" AND entity_id=?', (importer_ids[0],))
            else:
                q = f"SELECT id FROM assignments WHERE entity_type='importer' AND entity_id IN ({','.join(['?']*len(importer_ids))})"
                cur.execute(q, importer_ids)
            assignment_ids += [r['id'] for r in cur.fetchall()]
        
        if assignment_ids:
            q = f"SELECT SUM(amount) as s FROM payments WHERE assignment_id IN ({','.join(['?']*len(assignment_ids))})"
            cur.execute(q, assignment_ids)
            total_paid = cur.fetchone()['s'] or 0
        
        return float(total_assigned), float(total_paid)

    def get_unique_worker_names(self):
        """Get all unique worker names across all projects"""
        cur = self.conn.cursor()
        cur.execute('SELECT DISTINCT name FROM workers ORDER BY name')
        return [r['name'] for r in cur.fetchall()]

    def get_unique_jobs_for_worker(self, worker_name):
        """Get all unique jobs for a specific worker name across all projects"""
        cur = self.conn.cursor()
        cur.execute('SELECT DISTINCT job FROM workers WHERE name=? ORDER BY job', (worker_name,))
        return [r['job'] for r in cur.fetchall()]

    def get_all_jobs(self):
        """Get all unique jobs across all workers"""
        cur = self.conn.cursor()
        cur.execute('SELECT DISTINCT job FROM workers WHERE job IS NOT NULL ORDER BY job')
        return [r['job'] for r in cur.fetchall()]

    def get_worker_ids_by_name_and_job(self, name, job):
        """Get all worker IDs with the given name and job (could be in multiple projects)"""
        cur = self.conn.cursor()
        cur.execute('SELECT id FROM workers WHERE name=? AND job=?', (name, job))
        return [r['id'] for r in cur.fetchall()]

    def get_all_workers_with_totals(self):
        """Get all unique workers (by name+job combination) across all projects with combined totals"""
        cur = self.conn.cursor()
        # Get all unique (name, job) combinations
        cur.execute('''
            SELECT DISTINCT name, job FROM workers
            ORDER BY name, job
        ''')
        
        worker_groups = cur.fetchall()
        workers = []
        
        for group in worker_groups:
            name = group['name']
            job = group['job']
            
            # Find all worker IDs with this name+job combination
            cur.execute('SELECT id, project_id FROM workers WHERE name=? AND job=?', (name, job))
            worker_records = [dict(r) for r in cur.fetchall()]
            
            if not worker_records:
                continue
            
            # Get all projects for this worker
            projects = []
            for wr in worker_records:
                proj_id = wr['project_id']
                if proj_id:
                    cur.execute('SELECT name FROM projects WHERE id=?', (proj_id,))
                    proj_row = cur.fetchone()
                    if proj_row:
                        projects.append({'id': proj_id, 'name': proj_row['name']})
            
            # Calculate combined totals for all instances of this worker+job
            total_assigned = 0
            total_paid = 0
            
            for wr in worker_records:
                w_id = wr['id']
                # Get assigned total for this worker ID
                cur.execute('SELECT SUM(amount) as s FROM assignments WHERE entity_type="worker" AND entity_id=?', (w_id,))
                assigned = cur.fetchone()['s'] or 0
                total_assigned += assigned
                
                # Get paid total for this worker ID
                cur.execute('SELECT id FROM assignments WHERE entity_type="worker" AND entity_id=?', (w_id,))
                assign_ids = [r['id'] for r in cur.fetchall()]
                
                if assign_ids:
                    q = f"SELECT SUM(amount) as s FROM payments WHERE assignment_id IN ({','.join(['?']*len(assign_ids))})"
                    cur.execute(q, assign_ids)
                    paid = cur.fetchone()['s'] or 0
                    total_paid += paid
            
            workers.append({
                'name': name,
                'job': job,
                'projects': projects,
                'worker_ids': [wr['id'] for wr in worker_records],
                'total_assigned': float(total_assigned),
                'total_paid': float(total_paid),
                'total_remaining': float(total_assigned - total_paid)
            })
        
        return workers

    def get_unique_importer_names(self):
        """Get all unique importer names across all projects"""
        cur = self.conn.cursor()
        cur.execute('SELECT DISTINCT name FROM importers ORDER BY name')
        return [r['name'] for r in cur.fetchall()]

    def get_unique_goods_for_importer(self, importer_name):
        """Get all unique goods for a specific importer name across all projects"""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT DISTINCT a.good FROM assignments a
            JOIN importers i ON a.entity_id = i.id
            WHERE i.name=? AND a.entity_type='importer' AND a.good IS NOT NULL
            ORDER BY a.good
        ''', (importer_name,))
        return [r['good'] for r in cur.fetchall()]

    def get_all_goods_importers(self):
        """Get all unique goods across all importer assignments"""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT DISTINCT good FROM assignments 
            WHERE entity_type='importer' AND good IS NOT NULL 
            ORDER BY good
        ''')
        return [r['good'] for r in cur.fetchall()]

    def get_importer_id_by_name(self, name, project_id=None):
        """Get importer ID by name (optionally in specific project)"""
        cur = self.conn.cursor()
        if project_id:
            cur.execute('SELECT id FROM importers WHERE name=? AND project_id=?', (name, project_id))
        else:
            cur.execute('SELECT id FROM importers WHERE name=?', (name,))
        return cur.fetchone()['id'] if cur.fetchone() else None

    def get_importer_ids_by_name(self, name):
        """Get all importer IDs with the given name (could be in multiple projects)"""
        cur = self.conn.cursor()
        cur.execute('SELECT id FROM importers WHERE name=?', (name,))
        return [r['id'] for r in cur.fetchall()]

    def get_importer_ids_by_name_and_job(self, name, job):
        """DEPRECATED: Use get_importer_ids_by_name instead. Kept for backwards compatibility."""
        return self.get_importer_ids_by_name(name)

    def get_all_importers_with_totals(self):
        """Get all unique importers (by name) across all projects with combined totals and their goods"""
        cur = self.conn.cursor()
        # Get all unique importer names
        cur.execute('''
            SELECT DISTINCT name FROM importers
            ORDER BY name
        ''')
        
        importer_groups = cur.fetchall()
        importers = []
        
        for group in importer_groups:
            name = group['name']
            
            # Find all importer IDs with this name (across all projects)
            cur.execute('SELECT id, project_id FROM importers WHERE name=?', (name,))
            importer_records = [dict(r) for r in cur.fetchall()]
            
            if not importer_records:
                continue
            
            # Get all projects for this importer
            projects = []
            for ir in importer_records:
                proj_id = ir['project_id']
                if proj_id:
                    cur.execute('SELECT name FROM projects WHERE id=?', (proj_id,))
                    proj_row = cur.fetchone()
                    if proj_row:
                        projects.append({'id': proj_id, 'name': proj_row['name']})
            
            # Get all unique goods used by this importer (across all instances/projects)
            cur.execute('''
                SELECT DISTINCT good FROM assignments a
                JOIN importers i ON a.entity_id = i.id
                WHERE i.name=? AND a.entity_type='importer' AND a.good IS NOT NULL
                ORDER BY a.good
            ''', (name,))
            goods = [r['good'] for r in cur.fetchall()]
            
            # Calculate combined totals for all instances of this importer
            total_assigned = 0
            total_paid = 0
            
            for ir in importer_records:
                i_id = ir['id']
                # Get assigned total for this importer ID
                cur.execute('SELECT SUM(amount) as s FROM assignments WHERE entity_type="importer" AND entity_id=?', (i_id,))
                assigned = cur.fetchone()['s'] or 0
                total_assigned += assigned
                
                # Get paid total for this importer ID
                cur.execute('SELECT id FROM assignments WHERE entity_type="importer" AND entity_id=?', (i_id,))
                assign_ids = [r['id'] for r in cur.fetchall()]
                
                if assign_ids:
                    q = f"SELECT SUM(amount) as s FROM payments WHERE assignment_id IN ({','.join(['?']*len(assign_ids))})"
                    cur.execute(q, assign_ids)
                    paid = cur.fetchone()['s'] or 0
                    total_paid += paid
            
            importers.append({
                'name': name,
                'goods': goods,
                'projects': projects,
                'importer_ids': [ir['id'] for ir in importer_records],
                'total_assigned': float(total_assigned),
                'total_paid': float(total_paid),
                'total_remaining': float(total_assigned - total_paid)
            })
        
        return importers