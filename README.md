# vippool-clerk

���̃v���W�F�N�g�́AGoogle App Engine �œ��삷��A
�u���b�N�`�F�[���̏��擾�E�g�����U�N�V�����쐬�̕⏕���s���A�v���P�[�V�����ł��B

## �ł��邱��

�R�C���m�[�h�� RPC �Ŏ擾�ł���A�u���b�N���E�g�����U�N�V���������A
RDB �Ɋi�[���Ă��āA����� JSON �`���Ŏ擾�ł��܂��B

�R�C���m�[�h�� RPC �Ŏ擾�ł���g�����U�N�V�������ɂ́A
�ߋ��֌����������N�̏��͊i�[����Ă��܂����A���Ε����̃����N������܂���B
vippool-clerk �́A�����⊮���ĕԂ����߁A�������֐��������ł��B

�܂��A�R�C���A�h���X���Ƃ̎c�����ڂ� RDB �ɋL�^���Ă��܂��B
���̏������ɁA����A�v���Ȃǂ̍쐬���\�ƂȂ�܂��B

�Ō�ɁA�V�K�g�����U�N�V�����쐬�̕⏕�@�\�������Ă��܂��B
�g�����U�N�V�����쐬�� 2 �̃X�e�[�W�ɕ�����Ă���A
API �Ăяo���ŕԂ����n�b�V���ɑ΂��āA�N���C�A���g����
ECDSA �������쐬���A�ēx API ���Ăяo�����ƂŁA�g�����U�N�V�����쐬���������܂��B

���̂悤�ɁA�d�q�����쐬���N���C�A���g���ōs�����ƂŁA
�閧���̘R�k�̉\�����Ȃ������Ƃ��ł��܂��B

## API �̎g�p���@

���J���Ă��� API �ɂ��ẮAdoc/api.md �� API ���Ƃ̃}�j���A��������܂��̂ŁA
��������Q�Ƃ��Ă��������B

## �C���X�g�[�����@

�C���X�g�[���ɂ́A�ȉ��̂��̂��K�v�ł��B
1. Google App Engine �̃A�J�E���g
2. Google Cloud SQL �T�[�o
3. �R�C���m�[�h�T�[�o (Google Compute Engine �ŗ����グ�Ă���)

�܂��A�R�C���m�[�h�� 1 �䗧���グ�܂��B
�R�C���m�[�h�� conf �t�@�C���ɂ́A�ȉ��̋L�ڂ������Ă��������B
> "server=1
rpcuser=���[�U��
rpcpassword=�p�X���[�h
rpcport=�|�[�g�ԍ�
rpcallowip=0.0.0.0/0
txindex=1"

rpcallowip �́AGoogle App Engine �T�[�o���ǂ�����A�N�Z�X���邩�킩��Ȃ����߁A
�K�v�ł��B���z�l�b�g���[�N���\�z���āA���[�J�� IP �A�h���X�Ɍ��肵�Ă��ǂ��ł��B
txindex �́A�S�Ẵg�����U�N�V�����f�[�^���擾���邽�߂ɕK�v�ł��B

���ɁAGoogle Cloud SQL �̐ݒ���s���܂��B
MySQL �T�[�o�𗧂��グ�Ă��������B�ݒ�̓f�t�H���g�̂܂܂Ŗ�肠��܂��񂪁A
�p�t�H�[�}���X�������Ȃ���K�X��������ƂȂ��ǂ���������܂���B
�f�[�^�x�[�X�͎����ō쐬���邽�߁A���O�ɍ쐬����K�v�͂���܂���B
Google App Engine ����A�N�Z�X���邽�߂̃��[�U���쐬���Ă����Ă��������B

���ɁA�v���W�F�N�g�� server/config.py ��ҏW���܂��B
�f�t�H���g�ł͑S�ċ󗓂ɂȂ��Ă��邽�߁A
��قǐݒ肵���p�X���[�h����ݒ肵�Ă��������B

�Ō�ɁAGoogle App Engine �Ƀv���W�F�N�g���f�v���C���܂��B
���Ԃ����邽�߁A�ȉ��̏��Ԃɏ]���Ă��������B
> "gcloud app deploy app.yaml
gcloud app deploy queue.yaml
gcloud app deploy cron.yaml"

cron �� TaskQueue �Ƀf�[�^�����̃��N�G�X�g���������A
�����A�����������s���Ă����܂��B

�����グ��R�C���m�[�h��ύX����΁A�����̕ύX���K�v�ƂȂ邩������܂��񂪁A
���̃A���g�R�C���ł������\��������܂��B

## ���C�Z���X

(C) 2019-2019 VIPPOOL Inc.

���̃v���W�F�N�g�́AMIT ���C�Z���X�Œ񋟂���܂��B
