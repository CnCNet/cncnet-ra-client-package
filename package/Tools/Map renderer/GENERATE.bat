for %%A in (*.ini) do (
call RAFullMapPreviewGenerator.exe "%%A" --drawvisibleonly
)

for %%A in (*.mpr) do (
call RAFullMapPreviewGenerator.exe "%%A" --drawvisibleonly
)