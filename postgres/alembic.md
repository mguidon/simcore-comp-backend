### Cheatsheet for Alembic

Based on 

https://www.compose.com/articles/schema-migrations-with-alembic-python-and-postgresql/

```bash
1. pip install alembic
2. cd app directory
3. alembic init alembic
4. edit alembic.ini and alembic/env.py
5. model.py in baseline state
6. ./start_db
7. alembic revision -m "baseline"
8. copy baseline state of model into created py file
9. alembic upgrade head
10. Add more stuff to models.py
11. alembic revision --autogenerate -m "add basic stuff"
12. alembic upgrade head
```