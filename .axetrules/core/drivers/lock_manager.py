#!/usr/bin/env python3
"""
Gestor de bloqueos para prevenir análisis concurrentes.
Proporciona validación robusta y limpieza automática de bloqueos antiguos.

Uso:
    from lock_manager import LockManager
    
    lock = LockManager()
    if lock.acquire():
        try:
            # realizar análisis
        finally:
            lock.release()
"""
import os
import time
import sys

class LockManager:
    """Maneja el ciclo de vida de bloqueos de análisis."""
    
    def __init__(self, lock_file=".analysis.lock", max_age_seconds=3600):
        """
        Inicializa el gestor de bloqueos.
        
        Args:
            lock_file: Ruta al archivo de bloqueo
            max_age_seconds: Edad máxima del bloqueo antes de considerarlo obsoleto (default: 1 hora)
        """
        self.lock_file = lock_file
        self.max_age_seconds = max_age_seconds
        self.lock_acquired = False
    
    def is_locked(self):
        """Verifica si existe un bloqueo activo."""
        return os.path.exists(self.lock_file)
    
    def get_lock_info(self):
        """
        Lee información del archivo de bloqueo.
        
        Returns:
            dict con keys: analysis_type, timestamp, age_seconds
            None si el archivo no existe o está corrupto
        """
        if not self.is_locked():
            return None
        
        try:
            with open(self.lock_file, 'r') as f:
                content = f.read().strip()
            
            # Formato: ANALYSIS_IN_PROGRESS|<type>|<timestamp>
            parts = content.split('|')
            
            if len(parts) < 3:
                return None
            
            timestamp = float(parts[2])
            age = time.time() - timestamp
            
            return {
                'analysis_type': parts[1],
                'timestamp': timestamp,
                'age_seconds': age
            }
        except (ValueError, IOError, IndexError):
            return None
    
    def is_stale(self):
        """Verifica si el bloqueo existente es obsoleto."""
        info = self.get_lock_info()
        
        if info is None:
            return True  # Bloqueo corrupto = obsoleto
        
        return info['age_seconds'] > self.max_age_seconds
    
    def acquire(self, analysis_type="generic", force=False):
        """
        Intenta adquirir el bloqueo.
        
        Args:
            analysis_type: Tipo de análisis (branches, architecture, volumetry, etc.)
            force: Si True, fuerza la adquisición eliminando bloqueos obsoletos
        
        Returns:
            True si se adquirió el bloqueo, False en caso contrario
        """
        # Si ya tenemos el bloqueo, no hacer nada
        if self.lock_acquired:
            return True
        
        # Verificar si existe bloqueo
        if self.is_locked():
            info = self.get_lock_info()
            
            if info is None:
                # Bloqueo corrupto
                print("⚠️  Bloqueo corrupto detectado. Limpiando...")
                self._remove_lock()
            elif self.is_stale():
                # Bloqueo obsoleto
                age_minutes = int(info['age_seconds'] / 60)
                print(f"⚠️  Bloqueo antiguo detectado ({age_minutes} min). Limpiando...")
                self._remove_lock()
            else:
                # Bloqueo activo válido
                age_minutes = int(info['age_seconds'] / 60)
                print("\n❌ ANÁLISIS YA EN CURSO")
                print(f"   Tipo: {info['analysis_type']}")
                print(f"   Iniciado hace: {age_minutes} minuto(s)")
                print(f"\n   Opciones:")
                print(f"   1. Esperar a que termine el análisis actual")
                print(f"   2. Eliminar manualmente: {self.lock_file}")
                print(f"   3. Forzar con: --force (usar con precaución)\n")
                
                if not force:
                    return False
                
                print("⚠️  FORZANDO eliminación de bloqueo...")
                self._remove_lock()
        
        # Crear nuevo bloqueo
        try:
            with open(self.lock_file, 'w') as f:
                f.write(f"ANALYSIS_IN_PROGRESS|{analysis_type}|{time.time()}")
            
            self.lock_acquired = True
            print(f"🔒 Bloqueo establecido - Análisis '{analysis_type}' iniciado")
            return True
        
        except IOError as e:
            print(f"❌ Error creando bloqueo: {e}")
            return False
    
    def release(self):
        """Libera el bloqueo actual."""
        if not self.lock_acquired:
            return
        
        self._remove_lock()
        self.lock_acquired = False
        print("🔓 Bloqueo liberado")
    
    def _remove_lock(self):
        """Elimina el archivo de bloqueo."""
        if os.path.exists(self.lock_file):
            try:
                os.remove(self.lock_file)
            except OSError as e:
                print(f"⚠️  Error eliminando bloqueo: {e}")
    
    def __enter__(self):
        """Soporte para context manager."""
        if not self.lock_acquired:
            raise RuntimeError("Debe llamar acquire() antes de usar como context manager")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Libera el bloqueo automáticamente al salir del contexto."""
        self.release()
        return False

def main():
    """CLI para gestión manual de bloqueos."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestor de bloqueos RepoIntel")
    parser.add_argument('action', choices=['status', 'clear', 'force-clear'],
                       help='Acción a realizar')
    
    args = parser.parse_args()
    
    lock = LockManager()
    
    if args.action == 'status':
        if lock.is_locked():
            info = lock.get_lock_info()
            if info:
                age_min = int(info['age_seconds'] / 60)
                is_stale = " (OBSOLETO)" if lock.is_stale() else ""
                print(f"🔒 Bloqueo activo: {info['analysis_type']}{is_stale}")
                print(f"   Edad: {age_min} minuto(s)")
            else:
                print("🔒 Bloqueo existe pero está corrupto")
        else:
            print("✅ Sin bloqueo activo")
    
    elif args.action == 'clear':
        if lock.is_locked():
            if lock.is_stale():
                lock._remove_lock()
                print("✅ Bloqueo obsoleto eliminado")
            else:
                info = lock.get_lock_info()
                age_min = int(info['age_seconds'] / 60)
                print(f"⚠️  Bloqueo activo reciente ({age_min} min)")
                print("   Usa 'force-clear' para eliminar de todas formas")
        else:
            print("✅ Sin bloqueo para eliminar")
    
    elif args.action == 'force-clear':
        if lock.is_locked():
            lock._remove_lock()
            print("✅ Bloqueo eliminado forzadamente")
        else:
            print("✅ Sin bloqueo para eliminar")

if __name__ == "__main__":
    main()
