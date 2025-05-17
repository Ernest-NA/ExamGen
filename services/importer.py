import csv, json
from examgen import models as m

def import_csv(path: str, db_path: str = "examgen.db") -> None:
    engine = m.get_engine(db_path)
    session = m.Session(engine)
    with open(path, newline='', encoding="utf-8") as f:
        for row in csv.DictReader(f):
            subj = session.query(m.Subject).filter_by(name=row["subject"]).first() \
                   or m.Subject(name=row["subject"])
            q = m.MCQQuestion(
                prompt=row["prompt"],
                explanation=row.get("explanation"),
                subject=subj,
                meta=json.loads(row.get("meta", "{}")),
            )
            # …añadir opciones…
            session.add(q)
    session.commit()
