#!/usr/bin/env python3
"""
Script pour corriger la contrainte CHECK de la table backlog
pour permettre le type 'Capability'
"""

import sqlite3

def fix_db_constraint():
    conn = sqlite3.connect("orchestrator.db")
    cursor = conn.cursor()
    
    try:
        # Créer une table temporaire avec la bonne contrainte
        cursor.execute("""
            CREATE TABLE backlog_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                type TEXT CHECK(type IN ('Epic','Capability','Feature','US','UC')),
                parent_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                state TEXT,
                benefit_hypothesis TEXT,
                leading_indicators TEXT,
                mvp_definition TEXT,
                wsjf REAL,
                acceptance_criteria TEXT,
                story_points INTEGER,
                program_increment TEXT,
                iteration TEXT,
                owner TEXT,
                invest_compliant BOOLEAN DEFAULT 0,
                status TEXT,
                FOREIGN KEY(parent_id) REFERENCES backlog_new(id) ON DELETE CASCADE,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        """)
        
        # Copier les données de l'ancienne table
        cursor.execute("""
            INSERT INTO backlog_new 
            SELECT * FROM backlog
        """)
        
        # Supprimer l'ancienne table
        cursor.execute("DROP TABLE backlog")
        
        # Renommer la nouvelle table
        cursor.execute("ALTER TABLE backlog_new RENAME TO backlog")
        
        # Recréer les index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_backlog_parent ON backlog(parent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_backlog_project ON backlog(project_id)")
        
        conn.commit()
        print("✅ Contrainte CHECK mise à jour avec succès")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de la migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_db_constraint()