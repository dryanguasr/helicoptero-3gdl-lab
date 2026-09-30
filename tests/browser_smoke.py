"""Chromium smoke test for the exploratory laboratory UI."""
import csv
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path('review'); out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440,'height':1000}, device_scale_factor=1)
    errors=[]; stats={}
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto('http://127.0.0.1:4173/', wait_until='domcontentloaded')
        step=page.get_by_role('button',name='Paso',exact=False)
        step.wait_for(state='visible', timeout=180000)
        page.wait_for_function("!Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Paso')).disabled")
        assert 'β · pitch (+ motores hacia abajo)' in page.locator('.convention-strip').inner_text()
        assert page.get_by_role('link',name='Guía PDF',exact=False).get_attribute('href') == './guia-helicoptero-3gdl.pdf'
        step.click(); page.wait_for_function("document.querySelector('.time-overlay')?.textContent.includes('0.02')")
        page.wait_for_function("Number(document.querySelector('.scene').dataset.triangles)>0")
        page.locator('.scene').scroll_into_view_if_needed(); page.wait_for_function("document.querySelector('.scene').dataset.quality==='balanced'")
        stats['balanced']=page.locator('.scene').evaluate('(el)=>({...el.dataset})')
        assert int(stats['balanced']['triangles'])<12000 and int(stats['balanced']['drawCalls'])<100
        page.get_by_label('Modo ligero',exact=True).check(); page.wait_for_function("document.querySelector('.scene').dataset.quality==='lightweight'")
        stats['lightweight']=page.locator('.scene').evaluate('(el)=>({...el.dataset})')
        assert int(stats['lightweight']['triangles']) < int(stats['balanced']['triangles'])
        page.get_by_label('Modo ligero',exact=True).uncheck()
        # Exercise the shipped configuration through the real Pyodide worker.
        assert page.get_by_label('Ley de control',exact=True).input_value() == 'nonlinear'
        assert page.get_by_label('Referencia',exact=True).input_value() == 'multipoint'
        page.get_by_label('Velocidad de reproducción',exact=True).select_option('4')
        page.locator('.transport .primary').click()
        page.get_by_role('status').filter(has_text='Experimento completado').wait_for(timeout=120000)
        assert '60.00' in page.locator('.time-overlay').inner_text()
        with page.expect_download() as dl:
            page.get_by_role('button',name='↓ CSV',exact=True).click()
        route_path=out/'route.csv'; dl.value.save_as(route_path)
        with route_path.open() as f: route=list(csv.DictReader(f))
        import math
        for axis,tolerance in [('beta',.2),('gamma',.75)]:
            label='pitch' if axis=='beta' else 'yaw'
            errors_deg=[math.degrees(float(r[f'plant_{axis}_{label}_rad'])-float(r[f'reference_{axis}_{label}_rad'])) for r in route]
            assert math.sqrt(sum(e*e for e in errors_deg)/len(errors_deg)) < tolerance
        # Prepared local trial must reset time and restore a compatible operating point.
        page.get_by_role('button',name='Ensayo local · β = −15°',exact=True).click()
        page.wait_for_function("document.querySelector('.time-overlay')?.textContent.includes('0.00')")
        assert page.get_by_label('Ley de control',exact=True).input_value() == 'prefilter'
        assert float(page.get_by_label('β deseado · valor',exact=True).input_value()) == -15
        page.get_by_role('button',name='Ruta completa · no lineal',exact=True).click()
        page.wait_for_function("document.querySelector('select[aria-label=\"Ley de control\"]').value==='nonlinear'")
        page.get_by_role('button',name='C',exact=True).click(); page.wait_for_timeout(700)
        beta_input=page.get_by_label('β deseado · valor',exact=True)
        assert float(beta_input.input_value()) == 45
        control=page.get_by_label('Ley de control',exact=True)
        for mode in ['state','prefilter','integral','smc']:
            control.select_option(mode); page.wait_for_timeout(650)
            page.wait_for_function("!Array.from(document.querySelectorAll('button')).find(b=>b.textContent.includes('Paso')).disabled")
        page.get_by_role('button',name='Perturbación constante',exact=True).click(); page.wait_for_timeout(400)
        page.get_by_role('tab',name='No idealidades',exact=True).click()
        assert page.get_by_label('Perturbación constante',exact=True).is_checked()
        page.get_by_label('Velocidad de reproducción',exact=True).select_option('4')
        page.locator('.transport .primary').click()
        page.wait_for_function("parseFloat(document.querySelector('.time-overlay').textContent)>=5",timeout=30000)
        page.locator('.transport .primary').click(); page.wait_for_timeout(300)
        with page.expect_download() as dl:
            page.get_by_role('button',name='↓ CSV',exact=True).click()
        csv_path=out/'signals.csv'; dl.value.save_as(csv_path)
        with csv_path.open() as f: samples=list(csv.DictReader(f))
        assert len(samples)>150
        assert 'plant_beta_pitch_rad' in samples[0] and 'plant_beta_dot_rad_s' in samples[0]
        assert float(samples[-1]['reference_beta_pitch_rad']) > 0
        for label in ['Error','Plano γ–β','Roll α','Actuadores','Estimación','Error estimador','Velocidades','Seguimiento']:
            page.get_by_role('button',name=label,exact=True).click(); page.wait_for_timeout(90)
        page.get_by_role('tab',name='Estimación',exact=True).click()
        page.get_by_label('Realimentación',exact=True).select_option('ekf'); page.wait_for_timeout(900)
        page.get_by_label('Estimación',exact=True).check(); page.wait_for_timeout(250)
        page.screenshot(path=str(out/'desktop.png'),full_page=True)
        page.locator('.lab-viewer').screenshot(path=str(out/'viewer.png'))
        page.set_viewport_size({'width':390,'height':844}); page.wait_for_timeout(400)
        page.screenshot(path=str(out/'mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert not errors, '\n'.join(errors)
        (out/'browser-summary.json').write_text(json.dumps({'passed':True,'csv_rows':len(samples),'last_t':samples[-1]['t_s'],'viewports':['1440x1000','390x844']},indent=2))
    finally:
        (out/'graphics.json').write_text(json.dumps(stats,indent=2))
        (out/'browser-errors.json').write_text(json.dumps(errors,indent=2))
        browser.close()
