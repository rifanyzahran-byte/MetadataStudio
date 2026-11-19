import os, sys, json, csv, shutil, subprocess, threading, queue, datetime, tempfile, traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP='Metadata Studio — Batch Video Metadata Manager'
EXTS={'.mp4','.mov','.m4v','.mkv','.avi','.webm','.ts','.mts','.m2ts'}

def find_tool(name):
    exe=name+'.exe' if os.name=='nt' else name
    bases=[Path(sys.executable).resolve().parent, Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)), Path(__file__).resolve().parent]
    for base in bases:
        local=base/exe
        if local.exists(): return str(local)
    return shutil.which(name)

def run(cmd):
    kw={'capture_output':True,'text':True,'errors':'replace','stdin':subprocess.DEVNULL}
    if os.name=='nt': kw['creationflags']=subprocess.CREATE_NO_WINDOW
    return subprocess.run(cmd,**kw)

def utc_stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

class App:
    def __init__(self,root):
        self.root=root; root.title(APP); root.geometry('1130x760'); root.minsize(860,600)
        self.events=queue.Queue(); self.files=[]; self.busy=False; self.cancel=False
        self.folder=tk.StringVar(); self.out=tk.StringVar(); self.recursive=tk.BooleanVar(value=False)
        self.mode=tk.StringVar(value='Clean & update (lossless remux)')
        self.date_mode=tk.StringVar(value='Current date/time per file')
        self.custom=tk.StringVar(value=datetime.datetime.now().astimezone().isoformat(timespec='seconds'))
        self.title_mode=tk.StringVar(value='Use filename')
        self.title=tk.StringVar(); self.author=tk.StringVar(); self.comment=tk.StringVar()
        self.keep_tags=tk.BooleanVar(value=False); self.fsdate=tk.BooleanVar(value=True)
        self.overwrite=tk.BooleanVar(value=False); self.copy_sub=tk.BooleanVar(value=True); self.inplace=tk.BooleanVar(value=True)
        self.status=tk.StringVar(value='Ready — choose a folder to begin')
        self.make_ui(); self.root.after(100,self.poll)

    def make_ui(self):
        s=ttk.Style(); s.theme_use('clam')
        s.configure('TButton',padding=(9,6)); s.configure('TNotebook.Tab',padding=(15,8))
        main=ttk.Frame(self.root,padding=12); main.pack(fill='both',expand=True)
        ttk.Label(main,text='METADATA STUDIO',font=('Segoe UI',19,'bold')).pack(anchor='w')
        ttk.Label(main,text='Batch inspection, metadata editing, timestamps and safe lossless remux • Windows / Python',foreground='#56616e').pack(anchor='w',pady=(0,10))
        row=ttk.Frame(main); row.pack(fill='x')
        ttk.Label(row,text='Input folder',width=14).pack(side='left')
        ttk.Entry(row,textvariable=self.folder).pack(side='left',fill='x',expand=True)
        ttk.Button(row,text='Browse…',command=self.choose_folder).pack(side='left',padx=6)
        ttk.Button(row,text='Scan',command=self.scan).pack(side='left')
        row=ttk.Frame(main); row.pack(fill='x',pady=5)
        ttk.Label(row,text='Output folder',width=14).pack(side='left')
        ttk.Entry(row,textvariable=self.out).pack(side='left',fill='x',expand=True)
        ttk.Button(row,text='Browse…',command=self.choose_output).pack(side='left',padx=6)
        ttk.Checkbutton(row,text='Include subfolders',variable=self.recursive).pack(side='left')
        ttk.Checkbutton(row,text='EDIT ORIGINAL FILES (no copies)',variable=self.inplace).pack(side='left',padx=10)
        notebook=ttk.Notebook(main); notebook.pack(fill='both',expand=True,pady=8)
        tab1=ttk.Frame(notebook,padding=8); tab2=ttk.Frame(notebook,padding=8); tab3=ttk.Frame(notebook,padding=8)
        notebook.add(tab1,text='Video list'); notebook.add(tab2,text='Batch editor'); notebook.add(tab3,text='Deep inspector')
        self.tree=ttk.Treeview(tab1,columns=('name','size','date','path'),show='headings',selectmode='browse')
        for k,label,w in [('name','Filename',310),('size','Size (MB)',95),('date','Modified',165),('path','Location',420)]:
            self.tree.heading(k,text=label); self.tree.column(k,width=w,anchor='w')
        self.tree.pack(fill='both',expand=True,side='left')
        sb=ttk.Scrollbar(tab1,orient='vertical',command=self.tree.yview); sb.pack(side='left',fill='y'); self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind('<<TreeviewSelect>>',lambda e:self.inspect_selected())
        ed=ttk.Frame(tab2); ed.pack(fill='both',expand=True)
        ttk.Label(ed,text='Processing method').grid(row=0,column=0,sticky='w',pady=5)
        ttk.Combobox(ed,textvariable=self.mode,state='readonly',width=48,values=['Clean & update (lossless remux)','Update tags only (ExifTool; no remux)','Inspect only (no changes)']).grid(row=0,column=1,sticky='w')
        ttk.Label(ed,text='Timestamp source').grid(row=1,column=0,sticky='w',pady=5)
        ttk.Combobox(ed,textvariable=self.date_mode,state='readonly',width=48,values=['Current date/time per file','One custom date/time','Keep original file modification time']).grid(row=1,column=1,sticky='w')
        ttk.Label(ed,text='Custom timestamp (ISO 8601)').grid(row=2,column=0,sticky='w',pady=5)
        ttk.Entry(ed,textvariable=self.custom,width=51).grid(row=2,column=1,sticky='w')
        ttk.Label(ed,text='Title').grid(row=3,column=0,sticky='w',pady=5)
        ttk.Combobox(ed,textvariable=self.title_mode,state='readonly',width=48,values=['Use filename','Custom title','Remove title']).grid(row=3,column=1,sticky='w')
        ttk.Label(ed,text='Custom title').grid(row=4,column=0,sticky='w',pady=5)
        ttk.Entry(ed,textvariable=self.title,width=51).grid(row=4,column=1,sticky='w')
        ttk.Label(ed,text='Artist / creator').grid(row=5,column=0,sticky='w',pady=5)
        ttk.Entry(ed,textvariable=self.author,width=51).grid(row=5,column=1,sticky='w')
        ttk.Label(ed,text='Comment / description').grid(row=6,column=0,sticky='w',pady=5)
        ttk.Entry(ed,textvariable=self.comment,width=51).grid(row=6,column=1,sticky='w')
        ttk.Checkbutton(ed,text='Keep existing container tags (otherwise discard them)',variable=self.keep_tags).grid(row=7,column=0,columnspan=2,sticky='w',pady=5)
        ttk.Checkbutton(ed,text='Update Windows file modified/accessed timestamp',variable=self.fsdate).grid(row=8,column=0,columnspan=2,sticky='w',pady=5)
        ttk.Checkbutton(ed,text='Allow replacing files in output folder (backups are NOT made)',variable=self.overwrite).grid(row=9,column=0,columnspan=2,sticky='w',pady=5)
        ttk.Checkbutton(ed,text='Preserve input subfolder structure in output',variable=self.copy_sub).grid(row=10,column=0,columnspan=2,sticky='w',pady=5)
        ttk.Label(ed,text='Original files are never edited in lossless-remux mode. Video/audio streams are copied without re-encoding.\nSome embedded stream metadata and device fingerprints cannot be removed by container-tag editing.',foreground='#805b19',wraplength=760).grid(row=11,column=0,columnspan=2,sticky='w',pady=16)
        ed.columnconfigure(1,weight=1)
        bar=ttk.Frame(tab3); bar.pack(fill='x')
        ttk.Button(bar,text='Inspect selected video',command=self.inspect_selected).pack(side='left')
        ttk.Button(bar,text='Export scan report (CSV)',command=self.export_csv).pack(side='left',padx=5)
        ttk.Button(bar,text='Export full metadata (JSON)',command=self.export_json).pack(side='left')
        self.detail=tk.Text(tab3,wrap='none',font=('Consolas',10)); self.detail.pack(fill='both',expand=True,pady=7)
        self.log=tk.Text(main,height=6,wrap='word',font=('Consolas',9)); self.log.pack(fill='x')
        bottom=ttk.Frame(main); bottom.pack(fill='x',pady=(6,0))
        self.progress=ttk.Progressbar(bottom,mode='determinate'); self.progress.pack(side='left',fill='x',expand=True,padx=(0,8))
        ttk.Button(bottom,text='START BATCH',command=self.start).pack(side='left')
        ttk.Button(bottom,text='Cancel',command=self.stop).pack(side='left',padx=5)
        ttk.Label(main,textvariable=self.status).pack(anchor='w',pady=(4,0))
        self.log_line('FFmpeg: '+str(find_tool('ffmpeg') or 'not found')+' | FFprobe: '+str(find_tool('ffprobe') or 'not found')+' | ExifTool: '+str(find_tool('exiftool') or 'not found'))

    def choose_folder(self):
        p=filedialog.askdirectory();
        if p:
            self.folder.set(p); self.out.set(str(Path(p)/'METADATA_OUTPUT')); self.scan()
    def choose_output(self):
        p=filedialog.askdirectory();
        if p:self.out.set(p)
    def log_line(self,s):
        self.log.insert('end',s+'\n'); self.log.see('end')
    def scan(self):
        if self.busy:return
        p=Path(self.folder.get())
        if not p.is_dir():messagebox.showerror('Folder not found','Choose an existing input folder.');return
        output=Path(self.out.get()).resolve() if self.out.get() else (p/'METADATA_OUTPUT').resolve()
        iterator=p.rglob('*') if self.recursive.get() else p.iterdir()
        self.files=sorted([x for x in iterator if x.is_file() and x.suffix.lower() in EXTS and output not in x.resolve().parents],key=lambda x:str(x).lower())
        for x in self.tree.get_children():self.tree.delete(x)
        for i,f in enumerate(self.files):
            st=f.stat(); self.tree.insert('', 'end',iid=str(i),values=(f.name,f'{st.st_size/1048576:.1f}',datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),str(f.parent)))
        self.status.set(f'{len(self.files)} videos found'); self.log_line(f'Scanned: {len(self.files)} files')
    def selected_file(self):
        sel=self.tree.selection();return self.files[int(sel[0])] if sel else None
    def probe(self,f):
        data={'file':str(f),'filesystem':{'size_bytes':f.stat().st_size,'modified_local':datetime.datetime.fromtimestamp(f.stat().st_mtime).astimezone().isoformat(),'created_or_changed_local':datetime.datetime.fromtimestamp(f.stat().st_ctime).astimezone().isoformat()}}
        if find_tool('ffprobe'):
            p=run([find_tool('ffprobe'),'-v','error','-show_format','-show_streams','-show_chapters','-print_format','json',str(f)])
            data['ffprobe']=json.loads(p.stdout) if p.returncode==0 else {'error':p.stderr}
        if find_tool('exiftool'):
            p=run([find_tool('exiftool'),'-j','-G1','-a','-s','-ee',str(f)])
            try:data['exiftool']=json.loads(p.stdout)[0]
            except Exception:data['exiftool']={'error':p.stderr}
        return data
    def inspect_selected(self):
        f=self.selected_file()
        if not f:return
        def work():
            try:self.events.put(('detail',json.dumps(self.probe(f),indent=2,ensure_ascii=False)))
            except Exception as e:self.events.put(('log','Inspect failed: '+str(e)))
        threading.Thread(target=work,daemon=True).start()
    def export_csv(self):
        if not self.files:return
        p=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')]);
        if not p:return
        with open(p,'w',newline='',encoding='utf-8-sig') as fh:
            w=csv.writer(fh);w.writerow(['file','bytes','modified_local','path'])
            for f in self.files:w.writerow([f.name,f.stat().st_size,datetime.datetime.fromtimestamp(f.stat().st_mtime).astimezone().isoformat(),str(f)])
        self.log_line('Saved CSV: '+p)
    def export_json(self):
        if not self.files:return
        p=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')]);
        if not p:return
        def work():
            try:
                data=[self.probe(f) for f in self.files]
                with open(p,'w',encoding='utf-8') as fh:json.dump(data,fh,ensure_ascii=False,indent=2)
                self.events.put(('log','Saved detailed JSON: '+p))
            except Exception as e:self.events.put(('log','Export failed: '+str(e)))
        threading.Thread(target=work,daemon=True).start()
    def stop(self):self.cancel=True;self.status.set('Cancel requested — waiting for current file')
    def start(self):
        if self.busy:return
        if not self.files:self.scan()
        if not self.files:return
        mode=self.mode.get(); tool='exiftool' if mode.startswith('Update tags') else 'ffmpeg'
        if not mode.startswith('Inspect') and not find_tool(tool):messagebox.showerror('Missing tool',f'{tool} is required. Put its executable next to MetadataStudio.py or add it to PATH.');return
        if mode.startswith('Clean') and not find_tool('ffprobe'):self.log_line('Tip: install FFprobe for deeper inspection.')
        if not self.inplace.get() and not self.out.get():messagebox.showerror('Output required','Choose an output folder.');return
        inp=Path(self.folder.get()).resolve(); out=Path(self.out.get()).resolve() if self.out.get() else inp
        if not self.inplace.get() and out==inp:messagebox.showerror('Unsafe output','Output folder must differ from input folder.');return
        if self.inplace.get() and not mode.startswith('Inspect'):
            if not messagebox.askyesno('CONFIRM PERMANENT CHANGE','All selected ORIGINAL video files will be replaced in place. No backup copies will be created. Continue?'):return
        if self.date_mode.get()=='One custom date/time':
            try:datetime.datetime.fromisoformat(self.custom.get().replace('Z','+00:00'))
            except ValueError:messagebox.showerror('Invalid date','Use ISO 8601, e.g. 2026-11-20T08:30:00+07:00');return
        cfg={k:getattr(self,k).get() for k in ('mode','date_mode','custom','title_mode','title','author','comment','keep_tags','fsdate','overwrite','copy_sub','inplace')}
        self.busy=True;self.cancel=False;self.progress['maximum']=len(self.files);self.progress['value']=0
        threading.Thread(target=self.process,args=(list(self.files),inp,out,cfg),daemon=True).start()
    def process(self,files,inp,out,cfg):
        good=bad=0
        for idx,f in enumerate(files):
            if self.cancel:break
            try:
                rel=f.relative_to(inp) if cfg['copy_sub'] else Path(f.name)
                dest=f if cfg['inplace'] else out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                if not cfg['inplace'] and dest.exists() and not cfg['overwrite']:raise RuntimeError('Output exists; overwrite disabled')
                if cfg['date_mode']=='Current date/time per file':dt=datetime.datetime.now().astimezone()
                elif cfg['date_mode']=='One custom date/time':dt=datetime.datetime.fromisoformat(cfg['custom'].replace('Z','+00:00'))
                else:dt=datetime.datetime.fromtimestamp(f.stat().st_mtime).astimezone()
                iso=dt.isoformat(timespec='seconds'); title=f.stem if cfg['title_mode']=='Use filename' else cfg['title'] if cfg['title_mode']=='Custom title' else ''
                if cfg['mode'].startswith('Inspect'):
                    self.probe(f);good+=1;self.events.put(('log','Inspected: '+f.name));continue
                tmp=dest.with_name(dest.stem+'.__working__'+dest.suffix)
                if tmp.exists():raise RuntimeError('Temporary output exists: '+str(tmp))
                try:
                    if cfg['mode'].startswith('Clean'):
                        cmd=[find_tool('ffmpeg'),'-nostdin','-hide_banner','-loglevel','error','-i',str(f),'-map','0','-c','copy','-map_metadata','0' if cfg['keep_tags'] else '-1','-map_chapters','0' if cfg['keep_tags'] else '-1']
                        cmd+=['-metadata','creation_time='+iso,'-metadata','title='+title,'-metadata','artist='+cfg['author'],'-metadata','comment='+cfg['comment']]
                        if dest.suffix.lower() in ('.mp4','.mov','.m4v'):cmd+=['-movflags','use_metadata_tags']
                        cmd+=['-y',str(tmp)]
                        p=run(cmd)
                        if p.returncode:raise RuntimeError(p.stderr.strip()[-1000:] or 'FFmpeg failed')
                    else:
                        shutil.copy2(f,tmp)
                        cmd=[find_tool('exiftool'),'-overwrite_original','-P','-CreateDate='+iso,'-ModifyDate='+iso,'-Title='+title,'-Artist='+cfg['author'],'-Comment='+cfg['comment'],str(tmp)]
                        p=run(cmd)
                        if p.returncode:raise RuntimeError(p.stderr.strip()[-1000:] or 'ExifTool failed')
                    if cfg['fsdate']:
                        ts=dt.timestamp();os.utime(tmp,(ts,ts))
                    os.replace(tmp,dest);good+=1;self.events.put(('log','OK: '+str(dest)))
                finally:
                    if tmp.exists():tmp.unlink()
            except Exception as e:
                bad+=1;self.events.put(('log','ERROR: '+f.name+' — '+str(e)))
            finally:self.events.put(('progress',idx+1))
        self.events.put(('done',f'Finished: {good} succeeded, {bad} failed'+(' (cancelled)' if self.cancel else '')))
    def poll(self):
        try:
            while True:
                typ,val=self.events.get_nowait()
                if typ=='log':self.log_line(val)
                elif typ=='detail':self.detail.delete('1.0','end');self.detail.insert('end',val)
                elif typ=='progress':self.progress['value']=val;self.status.set(f'Processing {val}/{len(self.files)}')
                elif typ=='done':self.busy=False;self.status.set(val);self.log_line(val)
        except queue.Empty:pass
        self.root.after(100,self.poll)

if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()
