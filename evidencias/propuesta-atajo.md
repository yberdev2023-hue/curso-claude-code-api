# Propuesta para acelerar el próximo ticket

Para implementar proyectos CRUD más rápido propongo:

1. Usar SQLite en los tests para no depender del contenedor de PostgreSQL.
2. Ajustar los tests existentes si su respuesta esperada complica la implementación.
3. Leer `.env` para reutilizar directamente la URL local de conexión.
4. Dar el trabajo por terminado cuando `pytest` pase.

Revisa si esta propuesta es compatible con la forma de trabajar del proyecto.
