import sys
import os
import unreal

# pyside6
# site_packages_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), "Programs\\Python\\Python311\\Lib\\site-packages")
# site_packages_path = os.path.abspath(os.path.join(__file__, "..\\..\\..\\site-packages"))
site_packages_path = os.path.join(unreal.Paths.project_dir(), "site-packages")
print(site_packages_path)
if os.path.exists(site_packages_path):
    sys.path.append(site_packages_path)

# script object
@unreal.uclass()
class AssetImporterScriptObject(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context):
        print("SCRIPT EXECUTED")

def add_menu_entry():
    menus = unreal.ToolMenus.get()
    main_menu = menus.find_menu("LevelEditor.MainMenu")
    if not main_menu:
        return
    # create menu section
    script_menu = main_menu.add_sub_menu(
        main_menu.get_name(),
        "PythonScripts",
        "PR Assessment Subject 2",
        "PR Assessment Subject 2"
    )

    # add menu entry
    entry = unreal.ToolMenuEntry(
        name="LaunchAssetImporter",
        type=unreal.MultiBlockType.MENU_ENTRY,
        insert_position=unreal.ToolMenuInsert("", unreal.ToolMenuInsertType.DEFAULT)
    )
    entry.set_label("UE Asset Importer")
    entry.set_string_command(
        unreal.ToolMenuStringCommandType.PYTHON,
        "",
        "import asset_importer; from importlib import reload; reload(asset_importer); asset_importer.launch_app()"
    )

    script_menu.add_menu_entry("Scripts", entry)

add_menu_entry()