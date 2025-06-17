import os
# import yaml
import unreal

paths = unreal.Paths
root_asset_path = "/Game/Subject_2"

def validate_skeleton(skeletons):
    unreal.log("In validate_skeleton")
    # first we get each skeleton's bone hierarchy
    # store bone hierarchy in bone_map, bone_map[skeleton.name] = bone_hierarchy
    # create a group dict to group skeleton. we validate the length of bone_hierarchy
    # for skeleton in bone_map, if len(bone_hierarchy) not in group, append group[len(bone_hierarchy)] = [bone_name], else group[len(bone_hierarchy)].append(bone_name)    
    bone_map = {}
    for skeleton in skeletons:
        sk_obj = unreal.load_object(None, skeleton)
        if not isinstance(sk_obj, unreal.Skeleton):
            unreal.log_error(f"Invalid skeleton {skeleton}")
        bone_tree = sk_obj.get_editor_property("bone_tree")
        bone_hierarchy = [bone for bone in bone_tree]
        bone_map[skeleton] = bone_hierarchy

    group = {}
    for skeleton, bones in bone_map.items():
        if len(bones) not in group:
            group[len(bones)] = [skeleton]
        else:
            group[len(bones)].append(skeleton)

    # check number of groups. If group > 1, means we have more than one skeleton hierarchy
    if len(group) > 1:
        return ("[WARNING] More than one skeleton hierarchy found.", group)
    else:
        return "All skeletons are A-OK!"

def asset_import_task(asset_file, mode, options):
    # task settings
    task = unreal.AssetImportTask()
    task.automated = True
    task.destination_path = f"{root_asset_path}/SKM" if "SKM_" in asset_file else f"{root_asset_path}/ANIM"
    task.filename = asset_file
    task.options = options
    asset_name = os.path.basename(asset_file).strip(".fbx")
    existing_assets = [os.path.basename(asset).split('.')[0] for asset in get_all_assets() if asset_name in asset and 'Skeleton' not in asset and 'Physic' not in asset]
    try:
        latest = int(max(existing_assets).split('_')[-1])
        if mode == 'replace':
            task.replace_existing = True
        elif mode == 'import':
            task.replace_existing = False
            latest += 1
        task.destination_name = f"{asset_name}_{latest:03}"
    except:
        task.destination_name = f"{asset_name}_001"
    task.save = True
    return task

def skeletal_mesh_import_task(asset_file, mode='import'):
    # import data
    import_data = unreal.FbxSkeletalMeshImportData()

    # fbx options
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = True
    options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.skeletal_mesh_import_data = import_data

    task = asset_import_task(asset_file, mode, options)
    return task

def anim_sequence_import_task(asset_file, skeleton=None, mode='import'):
    # import data
    import_data = unreal.FbxAnimSequenceImportData()

    # fbx options
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = True
    options.import_animations = True
    options.import_mesh = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    options.anim_sequence_import_data = import_data
    options.skeleton = skeleton
    
    task = asset_import_task(asset_file, mode, options)
    return task

def get_all_assets():
    # get all asset paths in content browser
    eal = unreal.EditorAssetLibrary
    return eal.list_assets(root_asset_path)

def get_import_options():
    # ideally import options should be a separate config file for more control
    import_config_file = os.path.join(os.path.dirname(__file__), "import_config.yaml")
    if os.path.exists(import_config_file):
        with open(import_config_file, 'r') as file:
            config = yaml.safe_load(file)
            return config
        
def get_asset_tools():
    # asset tools to pass tasks
    return unreal.AssetToolsHelpers.get_asset_tools()