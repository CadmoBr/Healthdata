select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

with child as (
    select fk_facility as from_field
    from "healthdata_dw"."dw_gold"."fact_hospital_production"
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



      
    ) dbt_internal_test