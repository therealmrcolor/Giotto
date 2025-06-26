# frontend/app/forms.py
"""Flask-WTF forms for frontend input."""

from flask_wtf import FlaskForm
from wtforms import TextAreaField, StringField, SubmitField, IntegerField, HiddenField, SelectField
from wtforms.validators import DataRequired, Optional, ValidationError, NumberRange
import json

class CSRFDisabledForm(FlaskForm):
    """Base form class with CSRF protection disabled."""
    class Meta:
        csrf = False

class OptimizationInputForm(CSRFDisabledForm):
    colors_json = TextAreaField('Lista Colori (JSON):', validators=[], render_kw={"rows": 15, "cols": 70})
    start_cluster = StringField('Cluster Iniziale (Opzionale):', validators=[Optional()])
    sequence_type_selector = SelectField('Tipo Sequenza di Default:', 
                                       choices=[
                                           ('', 'Nessuno (Standard)'),
                                           ('piccola', 'Piccola (stesso giorno)'),
                                           ('successiva', 'Successiva (giorno dopo)')
                                       ],
                                       validators=[Optional()],
                                       default='')
    submit = SubmitField('Ottimizza Sequenza')

# --- NUOVI FORM PER LA GESTIONE DB ---

def validate_json_string(form, field):
    """Valida se la stringa è un JSON valido e una lista."""
    if field.data:
        try:
            data = json.loads(field.data)
            if not isinstance(data, list):
                raise ValidationError('Il campo Transition Colors JSON deve essere una lista JSON valida (es. ["RAL123", "CODE456"] o []).')
        except json.JSONDecodeError:
            raise ValidationError('Formato JSON non valido per Transition Colors.')
        except TypeError: # Handles if field.data is not a string (e.g. None from Optional)
            pass # Optional validator handles this

class CambioColoriRowForm(CSRFDisabledForm):
    source_cluster = HiddenField() # Usato per sapere a quale gruppo aggiungere, non modificabile nel form di riga
    destination_cluster = StringField('Destination Cluster:', validators=[DataRequired()])
    peso = IntegerField('Peso:', validators=[DataRequired(), NumberRange(min=0)])
    transition_colors = TextAreaField('Transition Colors (JSON List):', 
                                      validators=[Optional(), validate_json_string], 
                                      render_kw={"rows": 3, "placeholder": 'Es: ["RAL3020", "ABC"] oppure []'})
    required_trigger_type = StringField('Required Trigger Type:', 
                                        validators=[Optional()],
                                        render_kw={"placeholder": "Es: 'F' (lascia vuoto se non richiesto)"})
    submit = SubmitField('Salva Riga')

class NewSourceClusterForm(CSRFDisabledForm):
    source_cluster_name = StringField('Nuovo Source Cluster:', validators=[DataRequired()])
    submit = SubmitField('Aggiungi Source Cluster')

class ClusterColoriRowForm(CSRFDisabledForm):
    cluster_name = HiddenField() # Usato per sapere a quale gruppo aggiungere
    color_code = StringField('Codice Colore:', validators=[DataRequired()])
    submit = SubmitField('Salva Codice Colore')

class NewClusterForm(CSRFDisabledForm):
    cluster_name = StringField('Nuovo Nome Cluster:', validators=[DataRequired()])
    submit = SubmitField('Aggiungi Cluster')