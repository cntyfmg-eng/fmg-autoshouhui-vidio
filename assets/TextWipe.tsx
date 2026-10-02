import type {CSSProperties} from 'react';
import {Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {revealProgress} from './easing';

type TextWipeProps = {
  text: string;
  textAsset?: string | null;
  startFrame: number;
  durationFrames: number;
};

const textStyle = (fontSize: number, maxWidth: number): CSSProperties => ({
  fontFamily: 'system-ui, PingFang SC, Microsoft YaHei, sans-serif',
  fontSize,
  fontWeight: 400,
  lineHeight: 1.34,
  letterSpacing: '0.025em',
  color: '#171714',
  WebkitTextStroke: '0.7px #171714',
  margin: 0,
  maxWidth,
  textAlign: 'left',
  whiteSpace: 'pre-line',
  transform: 'rotate(-0.35deg)',
});

const fallbackFontSize = (text: string, wide: boolean) => {
  const lines = text.split('\n').filter(Boolean);
  const lineCount = Math.max(1, lines.length);
  const longestLine = Math.max(...lines.map((line) => line.length), 1);
  if (wide) {
    // 16:9 left caption column: narrower measure, taller box
    const widthLimited = Math.floor(470 / (longestLine * 1.08));
    const heightLimited = Math.floor(820 / (lineCount * 1.3));
    return Math.max(46, Math.min(84, widthLimited, heightLimited));
  }
  const widthLimited = Math.floor(850 / (longestLine * 1.08));
  const heightLimited = Math.floor(306 / (lineCount * 1.28));
  return Math.max(48, Math.min(82, widthLimited, heightLimited));
};

export const TextWipe: React.FC<TextWipeProps> = ({
  text,
  textAsset,
  startFrame,
  durationFrames,
}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  const progress = revealProgress(frame, startFrame, durationFrames);
  const wide = width >= 1600;
  const fontSize = fallbackFontSize(text, wide);

  if (textAsset) {
    return (
      <div
        style={{
          position: 'absolute',
          zIndex: 40,
          top: 86,
          left: 96,
          width: 888,
          height: 288,
          clipPath: `inset(0 ${100 - progress * 100}% 0 0)`,
          overflow: 'hidden',
        }}
      >
        <Img
          src={staticFile(textAsset)}
          style={{
            display: 'block',
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            objectPosition: 'left top',
            filter: 'brightness(1.025) contrast(1.035)',
          }}
        />
      </div>
    );
  }

  if (wide) {
    // 16:9: caption sits vertically centred in the left column, with a soft
    // hand-drawn underline accent to tie it to the storybook look.
    return (
      <div
        style={{
          position: 'absolute',
          zIndex: 40,
          top: 0,
          bottom: 0,
          left: 96,
          width: 540,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          clipPath: `inset(0 ${100 - progress * 100}% 0 0)`,
        }}
      >
        <p style={textStyle(fontSize, 500)}>{text}</p>
        <div
          style={{
            marginTop: 34,
            width: 132,
            height: 7,
            borderRadius: 4,
            background: '#d8a24a',
            opacity: 0.75,
            transform: 'rotate(-0.6deg)',
          }}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'absolute',
        zIndex: 40,
        top: 92,
        left: 104,
        right: 96,
        display: 'flex',
        justifyContent: 'flex-start',
        clipPath: `inset(0 ${100 - progress * 100}% 0 0)`,
      }}
    >
      <p style={textStyle(fontSize, 852)}>{text}</p>
    </div>
  );
};
