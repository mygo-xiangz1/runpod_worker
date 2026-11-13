from comfy_api.latest import ComfyExtension, io

from .photo_texture import adjust_photo


class PhotoTextureAdjust(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id='LocalPhotoTextureAdjust',
            display_name='照片质感调节 · Photo Texture',
            category='image/照片质感',
            description='本地 sRGB 照片后处理。默认不改变图像；总强度为0时原样通过。适用于RTX超分之后，不修复人体结构。',
            search_aliases=['照片', '质感', '曝光', '白平衡', 'photo', 'grain', 'realism'],
            inputs=[
                io.Image.Input('images', display_name='图像'),
                io.Float.Input('exposure_ev', display_name='01 曝光 EV', default=0.0, min=-3.0, max=3.0, step=0.01,
                               tooltip='在线性光中调整曝光。+1 EV为光强翻倍；建议先尝试±0.1～0.3。'),
                io.Float.Input('temperature', display_name='02 白平衡 · 冷←→暖', default=0.0, min=-100.0, max=100.0, step=1.0,
                               tooltip='负值偏冷，正值偏暖。相对RGB增益调节，不是相机绝对开尔文色温；建议±2～8。'),
                io.Float.Input('tint', display_name='03 白平衡 · 绿←→洋红', default=0.0, min=-100.0, max=100.0, step=1.0,
                               tooltip='负值偏绿，正值偏洋红。用于轻微纠正肤色偏色。'),
                io.Float.Input('highlights', display_name='04 高光 · 压低←→提亮', default=0.0, min=-100.0, max=100.0, step=1.0,
                               tooltip='主要影响亮部。负值柔化高光；无法恢复源图已经丢失的细节。'),
                io.Float.Input('shadows', display_name='05 阴影 · 压暗←→提亮', default=0.0, min=-100.0, max=100.0, step=1.0,
                               tooltip='主要影响暗部，保留黑位。人像可从+5～15开始。'),
                io.Float.Input('grain_amount', display_name='06 细微颗粒 · 强度 %', default=0.0, min=0.0, max=3.0, step=0.01,
                               tooltip='0关闭颗粒。单色明暗噪点，中间调稍强；建议0.10～0.35，1约等于中间调2.55个8位灰度级标准差。'),
                io.Int.Input('grain_size', display_name='07 颗粒 · 尺寸 px', default=1, min=1, max=4, step=1,
                             tooltip='1为细颗粒，2～4更粗；在最终输出分辨率上生成。'),
                io.Int.Input('grain_seed', display_name='08 颗粒 · 固定种子', default=12345, min=0, max=2147483647,
                             control_after_generate=False, tooltip='相同图像、参数与种子产生相同结果，不修改全局随机状态。'),
                io.Float.Input('mix', display_name='09 总强度 · 0为原图', default=1.0, min=0.0, max=1.0, step=0.01,
                               tooltip='0完全保留输入，1应用全部效果。可用0.5～0.8减弱处理。'),
            ],
            outputs=[io.Image.Output('image', display_name='调节后图像')],
        )

    @classmethod
    def execute(cls, images, exposure_ev=0.0, temperature=0.0, tint=0.0,
                highlights=0.0, shadows=0.0, grain_amount=0.0,
                grain_size=1, grain_seed=12345, mix=1.0):
        return io.NodeOutput(adjust_photo(images, exposure_ev, temperature, tint,
                                         highlights, shadows, grain_amount,
                                         grain_size, grain_seed, mix))


class PhotoTextureExtension(ComfyExtension):
    async def get_node_list(self):
        return [PhotoTextureAdjust]


async def comfy_entrypoint():
    return PhotoTextureExtension()
