"""Small local display; never authority, delivery or another context builder."""
def display(value):
    if 'life' in value:
        b=value['life'];rows=['生活视图（派生/非第二记忆） '+b['identity_id'],b['first_life_experience_ready']]
        rows.extend(m['task_type']+' | '+m['source_path']+' | '+m['state']+' | '+m['source_state'] for m in b['materials'])
        rows.extend('已核验工作法 '+str(x['method'])+' | '+x['state']+' | 来源 '+str(x['evidence_record_id']) for x in b['learning'])
        rows.extend('隔离技能 '+x['task']+' | '+x['record_id']+' | 未安装外部插件' for x in b['skills'])
        rows.append('成果目录 '+b['report_directory']);rows.append('可分享经历 '+str(len(b['shared_context']))+'（候选，不自动发送）')
        rows.extend(x['kind']+' | '+x['phase'] for x in b['journal']['entries'][:6])
        return '\n'.join(rows)
    if 'dialogue' in value:
        d=value['dialogue']
        if 'text' not in d:return d.get('state','等待处理')
        prefix='[模型候选，尚未完成真实质量验证] ' if d['render_state']=='UNVERIFIED_MODEL_WORDING' else ''
        return prefix+d['text']+'\n  ['+d['mode']+'; '+d['provider_state']+']'
    if 'approved_sources' in value:
        return '\n'.join(x['filename']+' | '+x['support_state']+' | '+str(x['source_memory_id'] or '尚无来源记忆') for x in value['approved_sources'])
    if 'view' in value:
        v=value['view'];living=v['living_self'];resources=v['resources']
        goals=', '.join(g['state'] for g in v['goals']) or '无'
        lessons=', '.join(j['state'] for j in value['learning']) or '无'
        return '\n'.join(('主体 '+value['identity_id'],value['provider']+' | 自主活动 '+value['autonomy'],
            '当前 '+living['current_activity']+' | 目标 '+goals+' | 学习 '+lessons,
            '模型调用 '+str(resources['calls'])+' | 待核验调用 '+str(resources['unresolved_calls']),
            '报告: '+(', '.join(value['reports']) or '尚无'), '来源记忆: '+(', '.join(living['source_memory_ids'][-4:]) or '尚无'),
            '外部发送关闭；/help 查看命令。'))
    if value.get('state')=='STARTED':
        r=value['resources'];return '独立主体已启动：'+value['identity_id']+'\n'+value['mode']+'；无需 AstrBot/QQ。\n内存上限 '+str(r['memory_address_space_limit_mb'])+' MiB；CPU affinity '+str(r['affinity_cpus'])+'；cgroup quota '+r['cgroup_cpu_max']+'\n可以直接输入一句话，或 /help。空闲时仅处理已批准的材料。'
    if value.get('state')=='STOPPING':return '已保存并退出；主体 '+value['summary']['identity_id']+'；报告 '+str(len(value['summary']['reports']))+' 份。'
    if value.get('activity'):
        return '活动：'+str(value.get('maintenance_stage') or value.get('intention'))+'；判断 '+str(value.get('judgment') or '维护切片')
    if 'commands' in value:return '\n'.join(value['commands'])+'\n普通文本直接输入；默认没有真实模型。'
    if value.get('state')=='INITIALIZED':return '初始化完成：'+value['identity_id']+'\n配置：'+value['config']+'\n使用 run --home 同一目录启动。'
    return __import__('json').dumps(value,ensure_ascii=False)
