from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from .models import ReportTable

def export_pdf(table:ReportTable,destination:Path)->Path:
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);pagesize=landscape(A4) if len(table.columns)>7 else A4;doc=SimpleDocTemplate(str(destination),pagesize=pagesize,rightMargin=24,leftMargin=24,topMargin=24,bottomMargin=24);styles=getSampleStyleSheet();story=[Paragraph(table.title,styles['Title']),Paragraph(table.filters_text or 'Relatório financeiro',styles['Normal']),Spacer(1,10)];data=[list(table.columns)]+[[str(v) for v in row] for row in table.rows]
    if table.total_cents is not None:data.append(['Total']+['']*(len(table.columns)-2)+[f'R$ {table.total_cents/100:,.2f}'])
    t=Table(data,repeatRows=1);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.25,colors.grey),('FONTSIZE',(0,0),(-1,-1),7),('VALIGN',(0,0),(-1,-1),'TOP')]));story.append(t);doc.build(story);return destination
