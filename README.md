# �͂��߂Đ݌v���� REST API

��c���̈֎q�����܂����B�Ј����C�����˗����A�����̒S���҂��Ή����I����܂ŁA��̉�ʂ͂ǂ�����ē����˗��������̂ł��傤���B���̋��ނł́A1���̏C���˗����肪����ɁAHTTP�ł���肷��񑩂������Ő݌v���܂��B

**[��1�́uAPI�Ƃ͉����v����ǂ�](docs/01-api.md)**�B�ǂނ����Ȃ�AWS�̃A�J�E���g���A�v���O���~���O�̌o�����s�v�ł��B��7�͂���́A�茳�œ���API�𓮂����܂��B

| �� | �ǂ񂾂��Ƃɂł��邱�� |
| --- | --- |
| [1�@API�Ƃ͉���](docs/01-api.md) | �t�@�C���A�g��API���A���ʂ��K�v�ɂȂ鎞�_����I�� |
| [2�@REST�ƃ��\�[�X](docs/02-rest.md) | �Ɩ��ň����ΏۂƁA���̕\�������߂� |
| [3�@�p�X�ƃp�����[�^](docs/03-addresses.md) | �ΏہA���������A���M���e��u�������� |
| [4�@���\�b�h�ƍđ�](docs/04-methods.md) | ����̈Ӗ��ƁA�ʐM���r�؂ꂽ�Ƃ��̈��������߂� |
| [5�@�����ƃG���[](docs/05-responses.md) | �Ăяo���������̍s����I�ׂ鉞�������� |
| [6�@�Ɩ���API�̌_��ɂ���](docs/06-contract.md) | ����\�A���͏����A�y�[�W����A�݊�����݌v���� |
| [7�@FastAPI�Ŏ���](docs/07-fastapi.md) | �o�^����폜�܂œ������AHTTP��Python��Ή��Â��� |
| [8�@AWS�ɔz�u����](docs/08-aws.md) | CDK��API Gateway�ALambda�AAurora���\�z���A�����t���ŌĂ� |
| [9�@�ʂ̋Ɩ��Ő݌v���Ă݂�](docs/09-practice.md) | ��c���\��̐݌v�Ă����A���f�̍������������ |

## �R�[�h�̓���

| �ꏊ | ���� |
| --- | --- |
| [package/app](package/app) | FastAPI�̎�t�A���͂̌��؁A�C���˗��̓ǂݏ��� |
| [package/db](package/db) | Alembic�ɂ��e�[�u���̍쐬�ƕύX���� |
| [package/infra](package/infra) | Python CDK�ɂ��AWS�\�� |
| [tests](tests) | ���p�҂��猩���鉞�����m�F����e�X�g |

�茳�ł�SQLite�AAWS�ł�Aurora PostgreSQL���g���܂��BHTTP�̌_��͋��ʂł��B�e�͂̏o�T�́A�d�l�̐߁A�݌v�w�j�A���i�̌����h�L�������g�ɕ����Ė{���̋߂��ɍڂ��Ă��܂��B
