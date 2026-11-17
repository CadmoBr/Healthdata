
    
    

with child as (
    select fk_municipality as from_field
    from "healthdata_dw"."dw_gold"."fact_hospital_production"
    where fk_municipality is not null
),

parent as (
    select sk_municipality as to_field
    from "healthdata_dw"."dw_gold"."dim_municipality"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


