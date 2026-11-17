select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select sk_facility
from "healthdata_dw"."dw_gold"."dim_health_facility"
where sk_facility is null



      
    ) dbt_internal_test