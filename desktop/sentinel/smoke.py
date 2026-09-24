"""Real native-widget acceptance test. Qt events + HTTP backend + actual Bandit."""
import json
import sys
import time
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

def run(window,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);app=QApplication.instance();errors=[];original=sys.excepthook
    def exception(kind,value,tb):errors.append(str(value));original(kind,value,tb)
    sys.excepthook=exception
    def wait(condition,timeout=20000):
        end=time.monotonic()+timeout/1000
        while time.monotonic()<end:
            app.processEvents();QTest.qWait(40)
            if errors:raise AssertionError('Qt callback failed: '+errors[-1])
            if condition():return
        raise AssertionError('UI condition timed out')
    result={'steps':[]}
    try:
        wait(lambda:window.pages['dashboard'].loaded);window.grab().save(str(output/'01-dashboard.png'));result['steps'].append('Native dashboard rendered from API')
        QTest.mouseClick(window.nav['events'],Qt.LeftButton);page=window.pages['events'];wait(lambda:len(page.rows)==6);page.search.setText('SQL');wait(lambda:len(page.rows)==2);page.search.clear();wait(lambda:len(page.rows)==6);page.table.selectRow(next(i for i,e in enumerate(page.rows) if e['id']=='demo-001'));QTest.mouseClick(page.open_button,Qt.LeftButton)
        event=window.pages['event'];wait(lambda:event.event_data is not None and event.project.currentData()=='demo-shop');QTest.mouseClick(event.start,Qt.LeftButton);wait(lambda:event.view.job and event.view.job['status'] in ('completed','failed'),40000)
        job=event.view.job;assert job['status']=='completed',job.get('error');assert job['correlation']['matches'][0]['finding']['cwe']=='CWE-89';assert len(job['correlation']['matches'][0]['chain'])==3;result['sql_job']=job['id'];result['steps'].append('Clicked SQL investigation: real Bandit + 3-function AST chain')
        window.navigate('job',job['id']);jp=window.pages['job'];wait(lambda:jp.view.job and jp.view.job['id']==job['id']);window.grab().save(str(output/'02-attack-code.png'));jp.view.tabs.setCurrentIndex(1);QTest.qWait(150);window.grab().save(str(output/'03-evidence.png'));assert jp.view.evidence.items;result['steps'].append('Native evidence tree and raw JSON viewer')
        jp.view.tabs.setCurrentIndex(2);QTest.qWait(100);jp.view.tabs.setCurrentIndex(3);QTest.qWait(100);result['steps'].append('Reviewer and execution timeline tabs')
        # Exercise report download without a modal OS save dialog.
        reports=[];window.client.download('/investigations/'+job['id']+'/report',reports.append);wait(lambda:bool(reports));assert b'CWE-89' in reports[0];(output/'demo-report.md').write_bytes(reports[0]);result['steps'].append('Markdown export contains evidence and remediation')
        window.navigate('event','demo-003');wait(lambda:event.event_data and event.event_data['id']=='demo-003' and event.project.currentData()=='demo-shop');QTest.mouseClick(event.start,Qt.LeftButton);wait(lambda:event.view.job and event.view.job['event']['id']=='demo-003' and event.view.job['status'] in ('completed','failed'),40000);assert event.view.job['correlation']['matches']==[];result['steps'].append('Negative health endpoint: no false code association')
        window.navigate('event','demo-002');wait(lambda:event.event_data and event.event_data['id']=='demo-002' and event.project.currentData()=='demo-shop');QTest.mouseClick(event.start,Qt.LeftButton);wait(lambda:event.view.job and event.view.job['event']['id']=='demo-002' and event.view.job['status'] in ('completed','failed'),40000);assert event.view.job['correlation']['matches'][0]['finding']['cwe']=='CWE-78';result['steps'].append('Command injection maps to shell=True sink')
        QTest.mouseClick(window.nav['audit'],Qt.LeftButton);audit=window.pages['audit'];wait(lambda:audit.scan is not None);QTest.mouseClick(audit.scan_button,Qt.LeftButton);wait(lambda:audit.scan_button.isEnabled() and audit.scan is not None,40000);assert len(audit.scan['findings'])>=2;wait(lambda:bool(audit.viewer.toPlainText()));window.grab().save(str(output/'04-code-audit.png'));result['steps'].append('Code tree, scanner, line highlight and snapshot viewer')
        QTest.mouseClick(window.nav['settings'],Qt.LeftButton);settings=window.pages['settings'];wait(lambda:settings.loaded);window.grab().save(str(output/'05-settings.png'));QTest.mouseClick(settings.save_button,Qt.LeftButton);wait(lambda:'配置已保存' in settings.notice.text());settings.test('llm');wait(lambda:'Mock Provider' in settings.notice.text());result['steps'].append('Settings save and Mock provider connection test')
        QTest.mouseClick(window.nav['reports'],Qt.LeftButton);wait(lambda:len(window.pages['reports'].rows)>=3);result['steps'].append('Completed reports persisted and listed')
        # Exercise live theme changes without losing investigation or editor state.
        from . import theme
        from .widgets import CodeViewer
        from PySide6.QtCore import QSettings
        for mode in ('light','dark'):
            window.theme_select.setCurrentIndex(window.theme_select.findData(mode))
            wait(lambda:window.theme.effective==mode)
            assert theme.CURRENT==mode
            assert QSettings(window.theme.settings.fileName(),QSettings.IniFormat).value('appearance/mode')==mode
            window.navigate('job',job['id']);wait(lambda:jp.view.job and jp.view.job['id']==job['id']);jp.view.tabs.setCurrentIndex(0);QTest.qWait(200)
            window.grab().save(str(output/('theme-'+mode+'-investigation.png')))
            window.navigate('audit');wait(lambda:bool(audit.viewer.toPlainText()));QTest.qWait(200);window.grab().save(str(output/('theme-'+mode+'-code.png')))
            assert audit.viewer.highlighter is not None
            window.navigate('dashboard');wait(lambda:window.pages['dashboard'].loaded);QTest.qWait(200);window.grab().save(str(output/('theme-'+mode+'-dashboard.png')))
        original_detector=window.theme.system_theme
        try:
            window.theme.system_theme=lambda:'light'
            window.theme_select.setCurrentIndex(window.theme_select.findData('system'));wait(lambda:theme.CURRENT=='light')
            window.theme.system_theme=lambda:'dark';window.theme.poll();assert theme.CURRENT=='dark'
        finally:window.theme.system_theme=original_detector;window.theme.apply()
        assert window.theme.mode=='system'
        result['steps'].append('Light/dark UI, charts, code, investigation, persisted preference and simulated system changes')
        window.grab().save(str(output/'01-dashboard.png'));result['status']='passed';result['qt_errors']=errors
    except Exception as e:
        result['status']='failed';result['error']=str(e);result['qt_errors']=errors;window.grab().save(str(output/'failure.png'))
    finally:
        sys.excepthook=original;(output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
