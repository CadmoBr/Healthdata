
    
    

with child as (
    select fk_facility as from_field
    from "healthdata_dw"."dw_gold"."fact_hospital_beds"
    where fk_facility is not null
),

parent as (
    select sk_facility as to_field
    from "healthdata_dw"."dw_gold"."dim_health_facility"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


