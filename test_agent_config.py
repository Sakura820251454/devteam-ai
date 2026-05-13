from playwright.sync_api import sync_playwright
import time

def test_agent_config_modal():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("1. 打开前端页面...")
        page.goto('http://localhost:3002')
        page.wait_for_load_state('networkidle')
        page.screenshot(path='d:/AIproject/devteam-ai/screenshots/01_initial.png', full_page=True)
        print("   截图已保存: 01_initial.png")

        print("\n2. 查找并点击配置按钮...")
        try:
            config_buttons = page.get_by_role('button', name='配置')
            if config_buttons.count() > 0:
                config_buttons.first.click()
                print("   点击了配置按钮")
            else:
                print("   未找到配置按钮，尝试其他选择器...")
                page.get_by_text('配置 Agent 团队').click()
        except Exception as e:
            print(f"   点击失败: {e}")

        time.sleep(1)
        page.wait_for_load_state('networkidle')
        page.screenshot(path='d:/AIproject/devteam-ai/screenshots/02_modal_open.png', full_page=True)
        print("   截图已保存: 02_modal_open.png")

        print("\n3. 测试预设团队选择 - 点击 Web 开发团队...")
        web_team = page.get_by_text('Web 开发团队').first
        web_team.click()
        time.sleep(0.5)

        page.screenshot(path='d:/AIproject/devteam-ai/screenshots/03_web_team_selected.png', full_page=True)
        print("   截图已保存: 03_web_team_selected.png")

        web_team_class = web_team.get_attribute('class')
        print(f"   Web团队按钮 class: {web_team_class}")
        if 'primary' in web_team_class or 'border-primary' in web_team_class:
            print("   ✓ Web 开发团队已选中")
        else:
            print("   ✗ Web 开发团队未被选中")

        print("\n4. 测试单选 - 点击后端开发团队...")
        backend_team = page.get_by_text('后端开发团队').first
        backend_team.click()
        time.sleep(0.5)

        page.screenshot(path='d:/AIproject/devteam-ai/screenshots/04_backend_team_selected.png', full_page=True)
        print("   截图已保存: 04_backend_team_selected.png")

        web_team_class_after = web_team.get_attribute('class')
        backend_team_class = backend_team.get_attribute('class')
        print(f"   Web团队按钮 class: {web_team_class_after}")
        print(f"   后端团队按钮 class: {backend_team_class}")

        if 'primary' not in web_team_class_after and 'primary' in backend_team_class:
            print("   ✓ 单选逻辑正常 - 只有后端团队被选中")
        else:
            print("   ✗ 单选逻辑有问题")

        print("\n5. 测试手动选择会清除预设团队选中状态...")
        pm_template = page.get_by_text('产品经理').first
        pm_template.click()
        time.sleep(0.5)

        page.screenshot(path='d:/AIproject/devteam-ai/screenshots/05_manual_select.png', full_page=True)
        print("   截图已保存: 05_manual_select.png")

        backend_team_class_after_manual = backend_team.get_attribute('class')
        print(f"   后端团队按钮 class: {backend_team_class_after_manual}")
        if 'primary' not in backend_team_class_after_manual:
            print("   ✓ 手动选择后预设团队已取消选中")
        else:
            print("   ✗ 手动选择后预设团队仍保持选中")

        print("\n6. 测试确认按钮...")
        confirm_button = page.get_by_text('确认配置')
        if confirm_button.count() > 0:
            print(f"   确认按钮文本: {confirm_button.first.text_content()}")
            is_disabled = confirm_button.first.get_attribute('disabled')
            print(f"   按钮禁用状态: {is_disabled}")

        print("\n测试完成！")
        browser.close()

if __name__ == '__main__':
    import os
    os.makedirs('d:/AIproject/devteam-ai/screenshots', exist_ok=True)
    test_agent_config_modal()
