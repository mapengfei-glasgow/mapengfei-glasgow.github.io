"""Render fixed-Q vortex surfaces from real simulated frames, using ParaView."""
import sys
import csv
from pathlib import Path
from paraview.simple import *
from PIL import Image
path=Path(sys.argv[1] if len(sys.argv)>1 else 'runs/main128').resolve()
out=path/'visualization'
frames=list(csv.DictReader((path/'frames.csv').open()))
view=CreateView('RenderView');view.ViewSize=[900,760]
view.UseColorPaletteForBackground=0;view.Background=[.035,.045,.065]
view.OrientationAxesVisibility=0
source=XMLImageDataReader(FileName=[str(out/('frame_'+frames[0]['step']+'.vti'))])
contour=Contour(Input=source);contour.ContourBy=['POINTS','Q'];contour.Isosurfaces=[60.]
display=Show(contour,view);ColorBy(display,('POINTS','vorticity_magnitude'))
lut=GetColorTransferFunction('vorticity_magnitude');lut.ApplyPreset('Cool to Warm (Extended)',True);lut.RescaleTransferFunction(0,150)
display.SetScalarBarVisibility(view,True)
bar=GetScalarBar(lut,view);bar.Title='Vorticity magnitude';bar.ComponentTitle='';bar.TitleFontSize=14;bar.LabelFontSize=12
outline=Outline(Input=source);edges=Show(outline,view);edges.DiffuseColor=[.6,.65,.7]
view.CameraPosition=[2.25,1.85,1.65];view.CameraFocalPoint=[.5,.5,.5];view.CameraViewUp=[0,0,1]
view.CameraParallelProjection=1;view.CameraParallelScale=.85
text=Text();text.Text='';label=Show(text,view);label.FontSize=16;label.Color=[1,1,1]
images=[]
for index,frame in enumerate(frames):
    source.FileName=[str(out/('frame_'+frame['step']+'.vti'))];source.UpdatePipeline()
    text.Text=f'GPU 3D vortex decay | t={float(frame["time"]):.3f}\nQ=60, fixed threshold; actual simulated fields'
    target=out/('vortices3d_'+frame['step']+'.png')
    SaveScreenshot(str(target),view,ImageResolution=[900,760])
    images.append(Image.open(target).convert('RGB'))
    print(f'Rendered {index+1}/{len(frames)}',flush=True)
images[0].save(out/'vortices3d.gif',save_all=True,append_images=images[1:],duration=120,loop=0)
