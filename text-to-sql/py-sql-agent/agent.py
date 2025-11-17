# agent.py
import sqlite3
import re
import ollama
from tabulate import tabulate

DB_PATH = "users.db"
MODEL = "phi3:latest"

# 🔍 Detect operation type
def detect_operation(query: str) -> str:
    """Detect if query is READ, CREATE, UPDATE, or DELETE"""
    q = query.lower()
    
    # DELETE operations
    if any(word in q for word in ['delete', 'remove', 'get rid of', 'drop']):
        return 'DELETE'
    
    # CREATE/INSERT operations
    if any(word in q for word in ['add', 'create', 'insert', 'new user', 'register']):
        return 'CREATE'
    
    # UPDATE operations
    if any(word in q for word in ['update', 'change', 'edit', 'modify', 'set']):
        return 'UPDATE'
    
    # Default to READ
    return 'READ'

# 📖 READ - Safe SELECT only
def execute_read(sql: str):
    """Execute SELECT queries safely"""
    if not sql.strip().lower().startswith("select"):
        raise ValueError("❌ Invalid SELECT query.")
    
    if "limit" not in sql.lower():
        sql = sql.rstrip("; \n") + " LIMIT 100;"
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql)
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

# ➕ CREATE - Add new user
def execute_create(name: str, age: int, email: str, department: str):
    """Insert a new user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, age, email, department) VALUES (?, ?, ?, ?)",
        (name, age, email, department)
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id

# ✏️ UPDATE - Modify user
def execute_update(user_id: int, **kwargs):
    """Update user fields"""
    allowed_fields = {'name', 'age', 'email', 'department'}
    fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
    
    if not fields_to_update:
        raise ValueError("No valid fields to update.")
    
    set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
    values = list(fields_to_update.values()) + [user_id]
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    conn.commit()
    rows_affected = cur.rowcount
    conn.close()
    return rows_affected

# 🗑️ DELETE - Remove user
def execute_delete(user_id: int):
    """Delete a user by ID"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    rows_affected = cur.rowcount
    conn.close()
    return rows_affected

# 🧠 Generate SQL for READ operations
def generate_read_sql(nl_query: str) -> str:
    prompt = f"""[INST]
You are a strict SQLite code generator. Respond with ONLY a single SELECT statement — no explanations, no markdown, no extra text.

Table: users
Columns: id (INT), name (TEXT), age (INT), email (TEXT), department (TEXT)

Rules:
- Use only SELECT
- Always include LIMIT 100
- End with semicolon

Examples:
User: "engineers" → SELECT * FROM users WHERE department = 'Engineering' LIMIT 100;
User: "over 30" → SELECT * FROM users WHERE age > 30 LIMIT 100;

User: "{nl_query}"
SQL: [/INST]"""
    
    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"temperature": 0.1}
    )
    
    raw = response["response"].strip()
    match = re.search(r"(SELECT\s+[^;]*;?)", raw, re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
        if not sql.endswith(";"):
            sql += ";"
        return sql
    
    q = nl_query.lower()
    if "count" in q or "how many" in q:
        return "SELECT COUNT(*) AS count FROM users LIMIT 1;"
    elif "engineer" in q:
        return "SELECT * FROM users WHERE department = 'Engineering' LIMIT 100;"
    elif "over" in q or "above" in q or ">" in q:
        age = re.search(r"(\d+)", q)
        age_val = int(age.group(1)) if age else 30
        return f"SELECT * FROM users WHERE age > {age_val} LIMIT 100;"
    elif "under" in q or "below" in q or "<" in q:
        age = re.search(r"(\d+)", q)
        age_val = int(age.group(1)) if age else 30
        return f"SELECT * FROM users WHERE age < {age_val} LIMIT 100;"
    
    return "SELECT * FROM users LIMIT 100;"

# 🧠 Extract CREATE parameters
def extract_create_params(query: str) -> dict:
    """Extract name, age, email, department from natural language"""
    params = {}
    
    # Extract age first
    age_match = re.search(r'age\s+([0-9]+)', query, re.IGNORECASE)
    if age_match:
        params['age'] = int(age_match.group(1))
    
    # Extract email
    email_match = re.search(r'email\s+([\w.+-]+@[\w-]+\.\w+)', query, re.IGNORECASE)
    if email_match:
        params['email'] = email_match.group(1)
    
    # Extract department - everything after 'department' keyword
    dept_match = re.search(r'department\s+([\w\s]+?)(?:\s*$)', query, re.IGNORECASE)
    if dept_match:
        params['department'] = dept_match.group(1).strip()
    
    # Extract name - everything between 'add' and 'age'
    # This pattern is more strict: captures words/spaces until 'age' keyword
    name_match = re.search(r'add\s+([^a][^g][^e].*?)\s+age', query, re.IGNORECASE)
    if not name_match:
        # Simpler pattern: just look for 'add' followed by words until age
        name_match = re.search(r'add\s+(.+?)\s+age', query, re.IGNORECASE)
    
    if name_match:
        params['name'] = name_match.group(1).strip()
    
    return params

# 🧠 Extract UPDATE parameters
def extract_update_params(query: str) -> dict:
    """Extract user ID and fields to update"""
    params = {}
    
    # Extract user ID
    id_match = re.search(r'(?:user\s+)?id[\s:]+([0-9]+)|user\s+([0-9]+)', query, re.IGNORECASE)
    if id_match:
        params['id'] = int(id_match.group(1) or id_match.group(2))
    
    # Extract fields to update
    if 'name' in query.lower():
        name_match = re.search(r'(?:to\s+|name\s+to\s+|name\s+)["\']?([^"\',;]+)["\']?', query, re.IGNORECASE)
        if name_match:
            params['name'] = name_match.group(1).strip()
    
    if 'age' in query.lower():
        age_match = re.search(r'age\s+(?:to\s+)?(\d+)', query, re.IGNORECASE)
        if age_match:
            params['age'] = int(age_match.group(1))
    
    if 'email' in query.lower():
        email_match = re.search(r'email\s+(?:to\s+)?([\w.+-]+@[\w-]+\.\w+)', query, re.IGNORECASE)
        if email_match:
            params['email'] = email_match.group(1)
    
    if 'department' in query.lower():
        dept_match = re.search(r'department\s+(?:to\s+)?["\']?([^"\',;]+)["\']?', query, re.IGNORECASE)
        if dept_match:
            params['department'] = dept_match.group(1).strip()
    
    return params

# 🧠 Extract DELETE parameters
def extract_delete_params(query: str) -> dict:
    """Extract user ID to delete"""
    params = {}
    
    # Extract user ID
    id_match = re.search(r'(?:user\s+)?id[\s:]+([0-9]+)|user\s+([0-9]+)|delete\s+(?:user\s+)?([0-9]+)', query, re.IGNORECASE)
    if id_match:
        params['id'] = int(id_match.group(1) or id_match.group(2) or id_match.group(3))
    
    return params

# 🚀 Main orchestrator
def run_agent(query: str, verbose: bool = True):
    """Main agent function that handles READ, CREATE, UPDATE, DELETE"""
    try:
        operation = detect_operation(query)
        if verbose:
            print(f"Operation: {operation}")
        
        if operation == 'READ':
            sql = generate_read_sql(query)
            if verbose:
                print(f"SQL: {sql}")
            result = execute_read(sql)
            if result:
                if verbose:
                    print(f"\nResults ({len(result)} rows):")
                    headers = list(result[0].keys())
                    rows = [[row[col] for col in headers] for row in result]
                    print(tabulate(rows, headers=headers, tablefmt="grid"))
            else:
                if verbose:
                    print("✅ No results found.")
            return result
        
        elif operation == 'CREATE':
            params = extract_create_params(query)
            if not all(k in params for k in ['name', 'age', 'email', 'department']):
                if verbose:
                    print("❌ Missing required fields. Please provide: name, age, email, department")
                return None
            
            user_id = execute_create(**params)
            if verbose:
                print(f"✅ User created successfully!")
                print(f"   ID: {user_id}")
                print(f"   Name: {params['name']}")
                print(f"   Age: {params['age']}")
                print(f"   Email: {params['email']}")
                print(f"   Department: {params['department']}")
            return {'id': user_id, **params}
        
        elif operation == 'UPDATE':
            params = extract_update_params(query)
            if 'id' not in params:
                if verbose:
                    print("❌ User ID not found. Please specify: user ID 1 set age 35")
                return None
            
            user_id = params.pop('id')
            if not params:
                if verbose:
                    print("❌ No fields to update specified.")
                return None
            
            rows_affected = execute_update(user_id, **params)
            if rows_affected > 0:
                if verbose:
                    print(f"✅ User {user_id} updated successfully!")
                    print(f"   Updated fields: {', '.join(params.keys())}")
                return {'id': user_id, **params}
            else:
                if verbose:
                    print(f"❌ User ID {user_id} not found.")
                return None
        
        elif operation == 'DELETE':
            params = extract_delete_params(query)
            if 'id' not in params:
                if verbose:
                    print("❌ User ID not found. Please specify: delete user 1")
                return None
            
            user_id = params['id']
            rows_affected = execute_delete(user_id)
            if rows_affected > 0:
                if verbose:
                    print(f"✅ User {user_id} deleted successfully!")
                return {'deleted': True, 'id': user_id}
            else:
                if verbose:
                    print(f"❌ User ID {user_id} not found.")
                return None
    
    except Exception as e:
        if verbose:
            print(f"❌ Error: {e}")
        return None

# 🔁 CLI
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_agent(" ".join(sys.argv[1:]))
    else:
        print("💬 SQL Agent with CRUD (Python + phi3 + SQLite)")
        print("Examples:")
        print("  READ:   python agent.py 'show engineers'")
        print("  CREATE: python agent.py 'add John Doe age 25 email john@example.com department IT'")
        print("  UPDATE: python agent.py 'update user 1 age 30'")
        print("  DELETE: python agent.py 'delete user 1'\n")
        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input or user_input.lower() in ("exit", "quit"):
                    break
                run_agent(user_input)
                print("─" * 50)
            except KeyboardInterrupt:
                break
        print("👋 Bye!")