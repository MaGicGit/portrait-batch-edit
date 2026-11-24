# Lightroom Classic SDK notes

Verified SDK concepts used by the plugin:
- `LrCatalog:getTargetPhoto()` can be used to ensure a photo is selected before relying on `getTargetPhotos()`.
- `LrCatalog:getTargetPhotos()` returns selected photos, or the whole filmstrip if no selection exists; always guard against no explicit target.
- `LrCatalog:setSelectedPhotos(activePhoto, otherSelectedPhotos)` sets selection.
- `LrCatalog:createVirtualCopies(copyName)` creates virtual copies for currently selected photos and must run in an asynchronous `LrTasks` task.
- `LrPhoto:requestJpegThumbnail(width, height, callback)` asynchronously requests a rendered JPEG preview.
- `LrPhoto:applyDevelopSettings(settings, historyName)` applies global Develop settings.
- `LrDevelopController.createNewMask("aiSelection", subtype)` exists from SDK 11.0 and must be called while Develop module is active.
- `LrPhoto` Develop settings include `MaskGroupBasedCorrections` from SDK 11.0, but the mask-group payload schema is not treated as a stable public contract here.

The plugin deliberately does not write `MaskGroupBasedCorrections` or automate local masks in v0.2. Confirm exact API details against the SDK distributed with the installed Lightroom Classic version.
