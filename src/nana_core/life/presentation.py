"""Small local display; never authority, delivery or another context builder."""
def provider_notice(code: str) -> str:
    """Human-readable operational notice; never model speech or an outcome."""
    reasons = {
        'PROVIDER_HOURLY_BUDGET': '过去一小时的模型调用额度已达到设定上限。',
        'PROVIDER_DAILY_BUDGET': '过去24小时的模型调用额度已达到设定上限。',
        'PROVIDER_PROFILE_DAILY_BUDGET': '这个模型服务过去24小时的调用额度已达到设定上限。',
        'PROVIDER_TOTAL_CALL_BUDGET': '本次授权的模型调用次数已经用完。',
        'PROVIDER_TOTAL_RESERVED_COST_BUDGET': '本次授权的可用预算不足。',
        'COGNITION_DAILY_BUDGET': '本周期的模型调用次数已达到设定上限。',
        'COGNITION_BYTE_BUDGET': '本周期的模型总用量已达到设定上限。',
        'COGNITION_COST_BUDGET': '本周期的模型费用预留已达到设定上限。',
        'BUDGET_DENIED': '当前模型的预算或用量设置还不能支持这次请求。',
        'REMOTE_COST_RESERVATION_REQUIRED': '模型调用预算还没有启用。',
        'PROVIDER_UNCONFIGURED': '还没有配置可用的聊天模型。',
        'RUNTIME_PROVIDER_UNBOUND': '模型设置已保存，运行中的连接还未启用。',
        'SECRET_UNAVAILABLE': '模型凭据尚未安全绑定。',
        'PROVIDER_TIMEOUT_BILLING_UNKNOWN': '这次回复超时，结果和费用仍待核对；不会自动重发。',
        'PROVIDER_WORKER_UNRESOLVED': '先前的模型请求仍在处理中，结果还不能确认。',
        'PROVIDER_WORKER_BOUND_PRE_DISPATCH': '仍有模型请求在处理中，这次没有再发出调用。',
        'PREEMPTED_NO_AUTOMATIC_RETRY': '生成过程已让位给新的输入，原请求结果仍待核对。',
        'WIRE_RESERVATION_CHANGED_NO_DISPATCH': '发送前的用量校验未通过，这次没有发出模型请求。',
        'COGNITION_SOURCE_OUTSIDE_CONTEXT_BUDGET': '准备回答所需的信息超出了当前设置的容量。',
        'INSUFFICIENT_CONTEXT_BUDGET': '准备回答所需的信息超出了当前设置的容量。',
        'PERSON_SELF_CONTEXT_BUDGET': '准备回答所需的信息超出了当前设置的容量。',
        'DIALOGUE_PRIVACY_DENIED': '这段内容超出了当前模型获准读取的范围。',
    }
    return reasons.get(code, '这次暂时无法生成回复，请查看模型状态。')


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
