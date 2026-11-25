return {
    LrSdkVersion = 11.0,
    LrSdkMinimumVersion = 11.0,
    LrToolkitIdentifier = "com.example.portraitbatchedit",
    LrPluginName = "Portrait Batch Edit",
    VERSION = { major = 0, minor = 3, revision = 0 },
    URLHandler = "ExportRequest.lua",
    LrLibraryMenuItems = {
        {
            title = "Portrait Batch Edit - Export Selected Previews",
            file = "ExportPreviews.lua",
        },
        {
            title = "Portrait Batch Edit - Apply Plan to Virtual Copies",
            file = "ApplyPlan.lua",
        },
    },
}
