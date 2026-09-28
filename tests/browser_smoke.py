"""Real Chromium smoke test against Vite preview, including downloaded files."""
import csv
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path('review')
out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto('http://127.0.0.1:4173/', wait_until='domcontentloaded')
        step = page.get_by_role('button', name='Un paso', exact=False)
        step.wait_for(state='visible', timeout=180000)
        page.wait_for_function("!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Un paso')).disabled")
        step.click()
        page.wait_for_function("document.querySelector('.time-overlay')?.textContent.includes('0.02')")
        assert page.locator('.convention-strip').inner_text().find('α · roll') >= 0
        page.wait_for_function("Number(document.querySelector('.scene').dataset.triangles) > 0")
        stats = {'balanced': page.locator('.scene').evaluate('(el)=>({...el.dataset})')}
        assert int(stats['balanced']['triangles']) < 12000
        assert int(stats['balanced']['drawCalls']) < 100
        page.get_by_label('Modo ligero', exact=True).check()
        page.wait_for_timeout(300)
        stats['lightweight'] = page.locator('.scene').evaluate('(el)=>({...el.dataset})')
        assert int(stats['lightweight']['triangles']) < int(stats['balanced']['triangles'])
        page.get_by_label('Modo ligero', exact=True).uncheck()
        page.get_by_role('button', name='Superior', exact=True).click()
        page.wait_for_timeout(300)
        page.get_by_role('button', name='3D', exact=True).click()
        page.get_by_role('button', name='D', exact=True).click()
        page.wait_for_timeout(700)
        page.get_by_label('Velocidad de reproducción', exact=True).select_option('4')
        page.get_by_role('button', name='Iniciar', exact=False).click()
        page.wait_for_function("parseFloat(document.querySelector('.time-overlay').textContent)>=8", timeout=30000)
        page.get_by_role('button', name='Pausar', exact=False).click()
        page.wait_for_timeout(500)
        with page.expect_download() as download:
            page.get_by_role('button', name='↓ CSV', exact=True).click()
        csv_path = out/'signals.csv'
        download.value.save_as(csv_path)
        with csv_path.open() as stream:
            samples = list(csv.DictReader(stream))
        assert len(samples) > 300
        assert 'plant_beta_dot_rad_s' in samples[0]
        assert 'post_saturation_uc_normalized' in samples[0]
        with page.expect_download() as download:
            page.get_by_role('button', name='Informe guiado', exact=False).click()
        download.value.save_as(out/'student-report.md')
        assert 'Hipótesis antes del ensayo' in (out/'student-report.md').read_text()
        page.screenshot(path=str(out/'desktop.png'), full_page=True)
        page.locator('.lab-viewer').screenshot(path=str(out/'viewer.png'))
        for label in ['Error de seguimiento', 'Plano γ–β', 'Roll α', 'Actuadores', 'Medición y estimación', 'Error del estimador', 'Velocidades', 'Seguimiento']:
            page.get_by_role('button', name=label, exact=True).click()
            page.wait_for_timeout(120)
        page.get_by_label('Instante de la simulación', exact=True).focus()
        page.get_by_label('Instante de la simulación', exact=True).press('Home')
        page.wait_for_function("document.querySelector('.time-overlay').textContent.includes('0.00')")
        page.get_by_role('button', name='Volver al último instante', exact=True).click()
        page.get_by_role('tab', name='Observador', exact=True).click()
        page.get_by_label('Fuente de realimentación', exact=True).select_option('ekf')
        page.wait_for_timeout(1000)
        page.get_by_label('Estimación', exact=True).check()
        page.wait_for_timeout(300)
        page.locator('.lab-viewer').screenshot(path=str(out/'estimator.png'))
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_timeout(500)
        page.screenshot(path=str(out/'mobile.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Horizontal overflow'
        assert not errors, '\n'.join(errors)
        (out/'graphics.json').write_text(json.dumps(stats, indent=2))
        (out/'browser-summary.json').write_text(json.dumps({'passed':True,'csv_rows':len(samples),'last_t':samples[-1]['t_s'],'viewports':['1440x1000','390x844'],'renderer':'Chromium / SwiftShader; not a hardware FPS benchmark'}, indent=2))
    finally:
        (out/'browser-errors.json').write_text(json.dumps(errors, indent=2))
        page.screenshot(path=str(out/'final-state.png'), full_page=True)
        browser.close()
