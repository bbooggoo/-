# DWG 엔진과 공개 테스트 도면

- 패키지: `@mlightcad/libredwg-web@0.7.10`, npm 라이선스 `GPL-3.0`.
- 업스트림: https://github.com/mlightcad/libredwg-web
- 정확한 릴리스 소스: `5909bd2bb87fa1168838e1295188f3ee603618eb`. npm provenance와 v0.7.10 태그 대응 확인.
- 소스 아카이브: https://codeload.github.com/mlightcad/libredwg-web/tar.gz/5909bd2bb87fa1168838e1295188f3ee603618eb
- 소스 아카이브 SHA-256: `821f1f42101a4605b320469e407f0b0c1a880235865a2e7a87c368af98f92fa2`.
- 배포 WASM SHA-256: `d8b78f6d5e63e6e178cf7343cfd08ebe798d75b6754c593e15d8f948b823e038`.
- `dist/COPYING.txt`에 라이선스 전문, `dist/licenses.html`에 사용자 고지와 대응 소스 다운로드 링크를 제공한다. 빌드가 검증된 전체 C/JS 소스 아카이브를 같은 서버에 복사한다. npm tarball만으로 대응 소스를 대신하지 않는다.
- DWG 파서 통합 파일 `dist/dwg-parser-worker.mjs`, `dist/native-audit.mjs`, `dist/cad-model.mjs`는 GPLv3 조건으로 제공한다. Worker 분리가 업스트림 라이선스 예외를 만든다고 주장하지 않는다.
- 공개 fixture: `dist/sample_2018.dwg` ← `test/test-data/sample_2018.dwg`, `tests/fixtures/2018__Line.dwg` ← `test/test-data/2018/Line.dwg`, `2018__Text.dwg` ← `test/test-data/2018/Text.dwg`, `example_2018.dwg` ← `test/test-data/example_2018.dwg`. 동일 릴리스 출처와 COPYING 적용. 실제 사용자 도면이 아니며 삼성전자 기준을 담지 않는다.

DWG를 브라우저에서 읽고 중간 객체 DB를 서버에 저장한다. 원시 객체 Handle을 변환 결과와 대조해 누락을 표시하며, 특정 DWG 버전·객체 종류의 전체 지원을 보장하지 않는다. 원본 DWG 쓰기는 구현하지 않았다.
