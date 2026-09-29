import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, OffthreadVideo, Sequence,
  interpolate, registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import active from './active-profile.json';

type Scene = {scene_id:string; estimated_duration_sec:number; media?:string; audio?:string;
  narration?:string; on_screen_text?:string; text_effect?:string; trim_in?:number; playback_rate?:number};
type Profile = {fps:number; aspect_ratio:string; scenes:Scene[]; soft_subtitles?:boolean};
const profile:Profile = active;
const frames = (s:Scene, fps:number) => Math.max(1, Math.round(s.estimated_duration_sec * fps));

const SceneView:React.FC<{scene:Scene; index:number; softSubtitles?:boolean}> = ({scene, index, softSubtitles}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config:{damping:16, stiffness:120}});
  const fade = interpolate(frame, [0, 12], [0, 1], {extrapolateRight:'clamp'});
  const text = scene.on_screen_text || scene.scene_id;
  const effect = scene.text_effect || 'fade';
  const displayed = effect === 'typewriter' ? [...text].slice(0, Math.floor(frame / 2)).join('') : text;
  const mediaStyle:React.CSSProperties = {width:'100%', height:'100%', objectFit:'cover'};
  return <AbsoluteFill style={{background:`linear-gradient(145deg, #0b1021, ${index % 2 ? '#35275e' : '#12475c'})`, color:'white', fontFamily:'Arial, sans-serif'}}>
    {scene.media && (/\.(mp4|mov|webm|mkv|avi)$/i.test(scene.media)
      ? <OffthreadVideo src={staticFile(scene.media)} style={mediaStyle} muted
          trimBefore={Math.round((scene.trim_in || 0) * fps)} playbackRate={scene.playback_rate || 1}/>
      : <Img src={staticFile(scene.media)} style={mediaStyle}/>)}
    <AbsoluteFill style={{background:'linear-gradient(transparent, rgba(0,0,0,.78))'}}/>
    <div style={{position:'absolute', left:40, top:42, fontSize:17, letterSpacing:3, color:'#7fe7df'}}>DIRECTION LAB / {String(index+1).padStart(2,'0')}</div>
    <AbsoluteFill style={{justifyContent:'center', padding:44}}>
      <div style={{fontSize:58, fontWeight:900, lineHeight:1.1, overflowWrap:'anywhere', opacity:effect==='fade'?fade:1,
        transform:`translateY(${effect==='slide'?(1-enter)*100:0}px) scale(${effect==='pop'?.6+enter*.4:1})`, textShadow:'0 4px 24px #0008'}}>{displayed}</div>
    </AbsoluteFill>
    {!softSubtitles && <div style={{position:'absolute', left:40, right:40, bottom:100, fontSize:27, lineHeight:1.4, textShadow:'0 2px 8px black'}}>{scene.narration}</div>}
    <div style={{position:'absolute', bottom:35, left:40, fontSize:15, color:'#b9ccd7'}}>PREVIEW • AUDIO MẪU • KHÔNG PHẢI BẢN CUỐI</div>
    {scene.audio && <Audio src={staticFile(scene.audio)}/>}
  </AbsoluteFill>;
};

const Preview:React.FC<{profile:Profile}> = ({profile}) => {
  let start = 0;
  return <AbsoluteFill>{profile.scenes.map((scene,index) => {
    const from = start; start += frames(scene, profile.fps);
    return <Sequence key={scene.scene_id} from={from} durationInFrames={frames(scene, profile.fps)}>
      <SceneView scene={scene} index={index} softSubtitles={profile.soft_subtitles}/>
    </Sequence>;
  })}</AbsoluteFill>;
};
const metadata = (p:Profile) => {
  const [rw,rh] = p.aspect_ratio.split(':').map(Number);
  const width = rw > rh ? 960 : rw === rh ? 720 : 540;
  return {width, height:Math.round(width * rh / rw / 2) * 2, fps:p.fps,
    durationInFrames:p.scenes.reduce((n,s)=>n+frames(s,p.fps),0) || 1};
};
registerRoot(() => <Composition id="Preview" component={Preview} defaultProps={{profile}}
  {...metadata(profile)} calculateMetadata={({props}) => metadata(props.profile)}/>);
