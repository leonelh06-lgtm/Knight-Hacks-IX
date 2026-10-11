"""Run autonomous overhead-camera boss, or calibrate without connecting motors."""
import argparse,asyncio,json,math,socket,sys,threading,time,uuid
from pathlib import Path
from queue import Queue,Empty
from .calibration import BoardCalibration
from .pursuit import PursuitController,Decision
from .protocol import validate_message,number
from .vision import OverheadTracker
from .ble import MotorLink

def camera_arg(value):
    return int(value) if str(value).isdigit() else value

def parse_args(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--camera',type=camera_arg,default=1)
    p.add_argument('--camera-backend',choices=['auto','v4l2','dshow','msmf'],default='auto')
    p.add_argument('--tag-id',type=int,default=0)
    p.add_argument('--config',default='rover-config.json')
    p.add_argument('--calibration',default='rover-calibration.json')
    p.add_argument('--dry-run',action='store_true',help='Never discover/connect BLE; only print intended commands')
    p.add_argument('--game-state-port',type=int,default=8766)
    p.add_argument('--rover-state-port',type=int,default=8767)
    p.add_argument('--frames',type=int,default=0,help='Exit after this many ticks (0 runs continuously)')
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--calibrate-intrinsics',action='store_true')
    modes.add_argument('--calibrate-board',action='store_true')
    modes.add_argument('--validate-calibration',action='store_true')
    modes.add_argument('--export-game-calibration',action='store_true')
    p.add_argument('--intrinsics',default='rover-intrinsics.json')
    p.add_argument('--checkerboard',nargs=2,type=int,default=[9,6],metavar=('COLS','ROWS'))
    p.add_argument('--square-mm',type=float)
    p.add_argument('--tag-height-mm',type=float)
    p.add_argument('--centre-offset-mm',nargs=2,type=float,metavar=('FORWARD','RIGHT'))
    p.add_argument('--arena-mm',nargs=4,type=float,metavar=('X','Y','WIDTH','HEIGHT'))
    p.add_argument('--projection-size',nargs=2,type=int,metavar=('WIDTH','HEIGHT'))
    p.add_argument('--game-calibration',default='game/fight/rover-calibration.json')
    args=p.parse_args(argv)
    if not 0<=args.tag_id<587 or not 0<=args.game_state_port<=65535 or not 0<=args.rover_state_port<=65535 or args.frames<0:p.error('Invalid tag, port or frame limit')
    return args

def read_config(path):
    return json.loads(Path(path).read_text())

def load_setup(args):
    config=read_config(args.config);calibration=BoardCalibration.load(args.calibration);data=calibration.data
    if data['camera']!=str(args.camera):raise ValueError('Calibration belongs to another overhead camera')
    if config.get('tag_id',args.tag_id)!=args.tag_id:raise ValueError('Configured rover tag ID differs from --tag-id')
    if len(data.get('projection_size',[]))!=2 or any(type(n)!=int or n<=0 for n in data['projection_size']):raise ValueError('Measured projection pixel dimensions required')
    if config.get('board')!={'width_mm':914.4,'height_mm':508}:raise ValueError('This calibration is for a 36 by 20 inch board')
    for field,limit in [('length_mm',914.4),('width_mm',508)]:number(config['footprint'][field],.01,limit)
    if config.get('verified') is True:
        number(config.get('stopping_distance_mm'),0,914.4);number(config.get('extra_margin_mm'),0,508)
    config={**config,'calibration_id':data['calibration_id'],'calibration_verified':data.get('verified') is True,
            'validation_error_mm':data.get('validation_error_mm'),'arena':data['arena']}
    return config,calibration

def export_game_calibration(calibration,path):
    d=calibration.data
    if d.get('verified') is not True or 'projection_size' not in d:raise ValueError('Validate calibration and projection size first')
    public={k:d[k] for k in ('calibration_id','verified','arena','projection_size')}
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(public,indent=2))
    print(f'Browser calibration exported to {p}; reload the page.',flush=True)

def diagnostic_line(sample,decision,now):
    age=max(0,(now-sample.captured_at)*1000)
    state='VALID' if sample.valid and sample.pose and age<=250 else 'STALE' if sample.valid and sample.pose else 'INVALID'
    pose=sample.pose
    coordinates=f'x={pose.x_mm:.1f} y={pose.y_mm:.1f}mm heading={math.degrees(pose.heading_rad):.1f}deg' if pose else 'pose unavailable'
    return f'{state} {coordinates} frame_age={min(age,60000):.0f}ms | {decision.status} | command {decision.command.decode()} | armed {decision.armed}'

def terminal_commands(commands):
    try:
        for line in sys.stdin:commands.put(line.strip().lower())
    finally:commands.put('EOF')

async def run_runtime(args,config,calibration,*,tracker_factory=OverheadTracker,link_factory=MotorLink,commands=None):
    controller=PursuitController(config)
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    tracker=None;link=None;link_task=None;stop=asyncio.Event();seq=0;run_id=str(uuid.uuid4())
    commands=commands if commands is not None else Queue()
    try:
        sock.bind(('127.0.0.1',args.game_state_port));sock.setblocking(False)
        tracker=tracker_factory(args.camera,args.tag_id,calibration,backend=args.camera_backend);tracker.start()
        def decision_source():
            controller.update_pose(tracker.latest())
            return controller.tick(time.monotonic())
        if not args.dry_run:
            link=link_factory(config.get('ble_name','Makeblock_LE001b10674482'),decision_source,on_fault=controller.disarm)
            link_task=asyncio.create_task(link.run(stop))
        print(f"Rover {'DRY RUN (no BLE)' if args.dry_run else 'BLE mode'}; game UDP {sock.getsockname()[1]}; waiting disarmed.",flush=True)
        print('Single-tag mode: keep camera/projector fixed; stop and recalibrate if either moves.',flush=True)
        print('g + Enter arms; x + Enter stops; q + Enter exits. B in browser prepares final level.',flush=True)
        last_print='';last_print_at=-1e9;tick_count=0;last=Decision(b'X',False,'waiting')
        while True:
            now=time.monotonic()
            for _ in range(100):
                try:raw,address=sock.recvfrom(16384)
                except BlockingIOError:break
                try:
                    m=validate_message(json.loads(raw))
                    if m['type']=='game_state':controller.update_game(m,now)
                    elif m['type']=='contact_ack' and controller.game and all(m[k]==controller.game[k] for k in ('session_id','calibration_id')):controller.ack_contact(m['event_id'])
                except (ValueError,TypeError,KeyError,AttributeError):controller.disarm('invalid game state')
            sample=tracker.latest();controller.update_pose(sample)
            if sample.error:raise RuntimeError(sample.error)
            if link_task and link_task.done():
                await link_task
                raise RuntimeError('BLE heartbeat ended')
            for _ in range(20):
                try:command=commands.get_nowait()
                except Empty:break
                if command in ('q','EOF'):stop.set()
                elif command=='x':controller.disarm('manual stop')
                elif command=='g':
                    if args.dry_run or (link and link.connected):controller.arm(now)
                    else:controller.disarm('BLE not connected')
            if stop.is_set():break
            last=controller.tick(now)
            pose=sample.pose
            valid=bool(sample.valid and pose and 0<=now-sample.captured_at<=.25 and 0<=pose.x_mm<=914.4 and 0<=pose.y_mm<=508 and math.isfinite(pose.heading_rad))
            if controller.game:
                g=controller.game
                telemetry=dict(type='rover_state',version=1,run_id=run_id,seq=seq,session_id=g['session_id'],calibration_id=calibration.data['calibration_id'],valid=valid,armed=last.armed,status=last.status[:128],frame_age_ms=min(60000,max(0,(now-sample.captured_at)*1000)),footprint=config['footprint'])
                if valid:telemetry['pose']=dict(x_mm=pose.x_mm,y_mm=pose.y_mm,heading_rad=pose.heading_rad)
                if args.rover_state_port:sock.sendto(json.dumps(telemetry).encode(),('127.0.0.1',args.rover_state_port))
                if last.contact_event and args.rover_state_port:sock.sendto(json.dumps(last.contact_event).encode(),('127.0.0.1',args.rover_state_port))
                seq+=1
            printed=diagnostic_line(sample,last,now)
            if last.status!=last_print or now-last_print_at>=1:
                print(printed,flush=True);last_print=last.status;last_print_at=now
            tick_count+=1
            if args.frames and tick_count>=args.frames:break
            await asyncio.sleep(.05)
        return Decision(b'X',False,'shutdown')
    finally:
        controller.disarm('shutdown');stop.set()
        if link:link.request_stop()
        if link_task:
            if not link_task.done():link_task.cancel()
            try:await link_task
            except (Exception,asyncio.CancelledError):pass
        if controller.game and args.rover_state_port:
            g=controller.game
            telemetry=dict(type='rover_state',version=1,run_id=run_id,seq=seq,session_id=g['session_id'],calibration_id=calibration.data['calibration_id'],valid=False,armed=False,status='shutdown',frame_age_ms=60000,footprint=config['footprint'])
            try:sock.sendto(json.dumps(telemetry).encode(),('127.0.0.1',args.rover_state_port))
            except OSError:pass
        if tracker:tracker.close()
        sock.close()

def main(argv=None):
    args=parse_args(argv)
    if args.calibrate_intrinsics:
        from .calibration_tools import calibrate_intrinsics
        if args.square_mm is None:raise ValueError('--square-mm must be measured')
        return calibrate_intrinsics(args.camera,args.camera_backend,args.intrinsics,*args.checkerboard,args.square_mm)
    if args.calibrate_board:
        from .calibration_tools import calibrate_board
        if any(v is None for v in (args.tag_height_mm,args.centre_offset_mm,args.arena_mm,args.projection_size)):raise ValueError('Measure tag height, offset, arena rectangle and projection pixel dimensions')
        arena=dict(zip(('x_mm','y_mm','width_mm','height_mm'),args.arena_mm))
        return calibrate_board(args.camera,args.camera_backend,args.intrinsics,args.calibration,args.tag_height_mm,args.centre_offset_mm,arena,args.projection_size)
    if args.validate_calibration:
        from .calibration_tools import validate_calibration
        return validate_calibration(args.camera,args.camera_backend,args.calibration,args.tag_id)
    if args.export_game_calibration:return export_game_calibration(BoardCalibration.load(args.calibration),args.game_calibration)
    config,calibration=load_setup(args)
    commands=Queue();threading.Thread(target=terminal_commands,args=(commands,),daemon=True).start()
    asyncio.run(run_runtime(args,config,calibration,commands=commands))

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('Rover stopped.',flush=True)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError) as error:raise SystemExit(f'Rover stopped: {error}') from error
