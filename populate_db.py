import os
from app import app, db, Pigment  # import  Flask app, db, and model

# list of pigments to populate
pigments_data = [
    {
        "kremer_id": "001",
        "pigment_name": "Azurite",
        "fcir": "",
        "cir": "",
        "image_truecolor": "Azurite_True-Color.png",
        "image_fcir": "Azurite_FCIR.png",
        "image_cir": "Azurite_IRR.png"
    },
    {
        "kremer_id": "002",
        "pigment_name": "Vermillion",
        "fcir": "",
        "cir": "",
        "image_truecolor": "Vermillion_True-Color.png",
        "image_fcir": "Vermillion_FCIR.png",
        "image_cir": "Vermillion_IRR.png"
    },
    {
        "kremer_id": "003",
        "pigment_name": "Madder Lake",
        "fcir": "",
        "cir": "",
        "image_truecolor": "Madder_Lake_True-Color.png",
        "image_fcir": "Madder_Lake_FCIR.png",
        "image_cir": "Madder_Lake_IRR.png"
    },
    {
        "kremer_id": "004",
        "pigment_name": "Malachite",
        "fcir": "",
        "cir": "",
        "image_truecolor": "Malachite_True-Color.png",
        "image_fcir": "Malachite_FCIR.png",
        "image_cir": "Malachite_IRR.png"
    },
    {
        "kremer_id": "005",
        "pigment_name": "Carmine Naccarat",
        "fcir": "",
        "cir": "",
        "image_truecolor": "Carmine_Naccarat_True-Color.png",
        "image_fcir": "Carmine_Naccarat_FCIR.png",
        "image_cir": "Carmine_Naccarat_IRR.png"
    },
    {
        "kremer_id": "006",
        "pigment_name": "Red Lead",
        "fcir": "",
        "cir": "",
        "image_truecolor": "Red_Lead_True-Color.png",
        "image_fcir": "Red_Lead_FCIR.png",
        "image_cir": "Red_Lead_CIR.png"
    }
    # add more pigments here
]

# run within Flask app context
with app.app_context():
    for data in pigments_data:
        # check if pigment already exists
        existing = Pigment.query.filter_by(kremer_id=data['kremer_id']).first()
        if not existing:
            pigment = Pigment(
                kremer_id=data['kremer_id'],
                pigment_name=data['pigment_name'],
                fcir=data['fcir'],
                cir=data['cir'],
                image_truecolor=data['image_truecolor'],
                image_fcir=data['image_fcir'],
                image_cir=data['image_cir']
            )
            db.session.add(pigment)
    db.session.commit()
    print("Database populated successfully!")
